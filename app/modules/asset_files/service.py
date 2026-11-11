import asyncio
import base64
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.redis_pubsub import RedisEventPublisher
from app.infrastructure.storage.s3_storage import S3Storage
from app.modules.asset.exceptions import AssetNotFoundError
from app.modules.asset.repositories import AssetRepository
from app.modules.asset_files.constants import MAX_FILE_SIZE
from app.modules.asset_files.exceptions import (
    AssetFileNotFoundError,
    AssetFileValidationError,
    DuplicateAssetFileError,
)
from app.modules.asset_files.models import AssetFiles
from app.modules.asset_files.repository import AssetFileRepository
from app.modules.asset_files.validation import validate_file
from app.modules.auth.exceptions import AuthorizationError
from app.modules.user.models import User
from app.shared.models.enums import FileType, FileUploadStatus, UserRole

logger = logging.getLogger(__name__)


def get_constraint_name(exc: IntegrityError) -> str | None:
    cause = getattr(exc.orig, "__cause__", None)

    if cause is None:
        return None

    return getattr(cause, "constraint_name", None)


class AssetFileService:
    def __init__(
        self,
        session: AsyncSession,
        storage: S3Storage | None = None,
        redis: Redis | None = None,
    ) -> None:
        self.session = session
        self.asset_repository = AssetRepository(session)
        self.repository = AssetFileRepository(session)
        self.storage = storage or S3Storage()
        self.event_publisher = RedisEventPublisher(redis) if redis is not None else None

    async def cleanup_s3(self, object_key: str) -> None:
        await asyncio.to_thread(
            self.storage.delete_object,
            object_key,
        )

    async def publish_file_event(
        self,
        *,
        event: str,
        asset_id: UUID,
        file_id: UUID,
        file_status: FileUploadStatus,
    ) -> None:
        if self.event_publisher is None:
            return

        try:
            await self.event_publisher.publish(
                event=event,
                data={
                    "asset_id": str(asset_id),
                    "file_id": str(file_id),
                    "status": file_status.value,
                },
            )
        except Exception:
            logger.exception(
                "Failed to publish asset file event",
                extra={
                    "asset_id": str(asset_id),
                    "file_id": str(file_id),
                    "event": event,
                },
            )

    async def reject_upload(
        self,
        file: AssetFiles,
        message: str,
    ) -> None:

        file.status = FileUploadStatus.FAILED
        file.updated_at = datetime.now(UTC)
        await self.session.commit()

        await self.publish_file_event(
            event="asset_file_failed",
            asset_id=file.asset_id,
            file_id=file.id,
            file_status=file.status,
        )

        await self.cleanup_s3(file.s3_object_key)

        raise AssetFileValidationError(message)

    async def process_s3_upload_event(
        self,
        *,
        object_key: str,
    ) -> AssetFiles:
        file = await self.repository.get_by_object_key(object_key)

        if file is None:
            raise AssetFileNotFoundError()

        return await self.confirm_upload(
            asset_id=file.asset_id,
            file_id=file.id,
        )

    async def cleanup_expired_pending_uploads(
        self, *, max_age: timedelta = timedelta(hours=24)
    ) -> dict[str, int]:
        cutoff = datetime.now(UTC) - max_age
        expired_files = await self.repository.list_expired_pending(cutoff=cutoff)

        # Keep plain values so a rollback cannot expire attributes we still need.
        candidates = [(file.id, file.s3_object_key) for file in expired_files]

        cleaned = 0
        failed = 0

        for file_id, object_key in candidates:
            try:
                # Re-fetch the record because its state may have changed since
                # the initial expired-files query.
                file = await self.repository.get_by_id(file_id)

                if (
                    file is None
                    or file.status != FileUploadStatus.PENDING
                    or file.deleted_at is not None
                ):
                    continue

                # Delete the S3 object only after confirming the record is eligible.
                await asyncio.to_thread(
                    self.storage.delete_object,
                    object_key,
                )

                now = datetime.now(UTC)
                file.status = FileUploadStatus.DELETED
                file.deleted_at = now
                file.updated_at = now

                await self.session.commit()
                cleaned += 1

            except Exception:
                await self.session.rollback()
                failed += 1

        return {
            "found": len(candidates),
            "cleaned": cleaned,
            "failed": failed,
        }

    async def prepare_uploads(
        self,
        *,
        asset_id: UUID,
        files: list[dict],
    ) -> dict:
        """Create pending file records and generate URLs without committing."""

        validated_files = []
        seen_checksums = set()

        # Validate all files and check for duplicates before creating records.
        for file_data in files:
            filename = file_data["filename"]
            content_type = FileType(file_data["content_type"])
            file_size = file_data["file_size"]
            checksum_sha256 = file_data["checksum_sha256"].lower()

            if checksum_sha256 in seen_checksums:
                raise DuplicateAssetFileError()

            existing_file = await self.repository.get_by_asset_and_checksum(
                asset_id=asset_id,
                checksum_sha256=checksum_sha256,
            )

            if existing_file is not None:
                raise DuplicateAssetFileError()

            seen_checksums.add(checksum_sha256)

            try:
                validate_file(
                    filename,
                    content_type.value,
                    file_size,
                )
            except ValueError as exc:
                raise AssetFileValidationError(str(exc)) from exc

            validated_files.append(
                {
                    "filename": filename,
                    "content_type": content_type,
                    "file_size": file_size,
                    "checksum_sha256": checksum_sha256,
                }
            )

        pending_files = []

        for file_data in validated_files:
            object_key = f"assets/{asset_id}/{uuid4()}-{file_data['filename']}"

            file = AssetFiles(
                asset_id=asset_id,
                original_file_name=file_data["filename"],
                content_type=file_data["content_type"],
                file_size=file_data["file_size"],
                checksum_sha256=file_data["checksum_sha256"],
                s3_object_key=object_key,
                status=FileUploadStatus.PENDING,
            )

            await self.repository.create(file)
            pending_files.append(file)

        upload_results = []

        for file in pending_files:
            checksum_bytes = bytes.fromhex(file.checksum_sha256)
            checksum_base64 = base64.b64encode(checksum_bytes).decode("ascii")

            upload_url = self.storage.generate_presigned_put_url(
                object_key=file.s3_object_key,
                content_type=file.content_type.value,
                checksum_sha256=checksum_base64,
            )

            upload_results.append(
                {
                    "file_id": file.id,
                    "upload_url": upload_url,
                    "expires_in": self.storage.PUT_URL_EXPIRY_SECONDS,
                    "headers": {
                        "Content-Type": file.content_type.value,
                        "x-amz-checksum-sha256": checksum_base64,
                    },
                }
            )

        return {"files": upload_results}

    async def create_uploads(
        self,
        *,
        asset_id: UUID,
        files: list[dict],
    ) -> dict:
        try:
            asset = await self.asset_repository.get_by_id(asset_id)

            if asset is None:
                raise AssetNotFoundError()

            result = await self.prepare_uploads(
                asset_id=asset_id,
                files=files,
            )

            await self.session.commit()
            return result

        except IntegrityError as exc:
            await self.session.rollback()

            constraint_name = get_constraint_name(exc)

            if constraint_name == "uq_asset_files_asset_id_checksum_sha256":
                raise DuplicateAssetFileError() from exc

            raise

        except Exception:
            await self.session.rollback()
            raise

    async def confirm_upload(
        self,
        *,
        asset_id: UUID,
        file_id: UUID,
    ) -> AssetFiles:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        file = await self.repository.get_by_id(
            file_id,
            for_update=True,
        )

        if file is None or file.asset_id != asset_id:
            raise AssetFileNotFoundError()

        if file.status == FileUploadStatus.UPLOADED:
            return file

        if file.status != FileUploadStatus.PENDING:
            raise AssetFileValidationError()

        metadata = await asyncio.to_thread(
            self.storage.get_object_metadata,
            file.s3_object_key,
        )

        if metadata is None:
            await self.reject_upload(file=file, message="File does not exist in S3")

        actual_size = metadata["content_length"]
        actual_content_type = metadata["content_type"]

        if actual_size is None or actual_size <= 0:
            await self.reject_upload(file=file, message="Uploaded file is empty")

        if actual_size > MAX_FILE_SIZE:
            await self.reject_upload(
                file=file, message="Uploaded file exceeds the 5 MB limit"
            )

        if actual_size != file.file_size:
            await self.reject_upload(
                file=file,
                message=(
                    f"File size mismatch: expected {file.file_size} got {actual_size}"
                ),
            )

        if actual_content_type != file.content_type.value:
            await self.reject_upload(
                file=file,
                message=(
                    f"Content type mismatch: expected {file.content_type.value} got {actual_content_type}"
                ),
            )

        if not file.checksum_sha256:
            await self.reject_upload(
                file=file,
                message="Expected file checksum is missing",
            )

        actual_checksum = metadata.get("checksum_sha256")

        if actual_checksum is None:
            await self.reject_upload(
                file=file,
                message="S3 checksum is missing",
            )

        expected_checksum = base64.b64encode(
            bytes.fromhex(file.checksum_sha256)
        ).decode("ascii")

        if actual_checksum != expected_checksum:
            await self.reject_upload(
                file=file,
                message="File checksum mismatch",
            )

        file.status = FileUploadStatus.UPLOADED
        file.uploaded_at = datetime.now(UTC)
        file.updated_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(file)

        await self.publish_file_event(
            event="asset_file_uploaded",
            asset_id=file.asset_id,
            file_id=file.id,
            file_status=file.status,
        )

        return file

    async def list_files(
        self,
        *,
        asset_id: UUID,
        current_user: User,
    ) -> list[dict]:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        if current_user.role != UserRole.ADMIN and asset.assigned_to != current_user.id:
            raise AuthorizationError()

        files = await self.repository.list_uploaded_for_asset(asset_id)

        return [
            {
                "file_id": file.id,
                "asset_id": file.asset_id,
                "original_file_name": file.original_file_name,
                "content_type": file.content_type.value,
                "file_size": file.file_size,
                "status": file.status.value,
                "uploaded_at": file.uploaded_at,
                "download_url": self.storage.generate_presigned_get_url(
                    file.s3_object_key
                ),
                "expires_in": 900,
            }
            for file in files
        ]

    async def delete_file(
        self,
        *,
        asset_id: UUID,
        file_id: UUID,
    ) -> None:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        file = await self.repository.get_by_id(file_id)

        if file is None or file.asset_id != asset_id:
            raise AssetFileNotFoundError()

        if file.status == FileUploadStatus.DELETED:
            return

        file.status = FileUploadStatus.DELETED
        file.deleted_at = datetime.now(UTC)
        file.updated_at = datetime.now(UTC)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await asyncio.to_thread(
            self.storage.delete_object,
            file.s3_object_key,
        )
