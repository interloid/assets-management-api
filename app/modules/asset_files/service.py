import asyncio
import base64
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    ) -> None:
        self.session = session
        self.asset_repository = AssetRepository(session)
        self.repository = AssetFileRepository(session)
        self.storage = storage or S3Storage()

    async def cleanup_s3(self, object_key: str) -> None:
        await asyncio.to_thread(
            self.storage.delete_object,
            object_key,
        )

    async def reject_upload(
        self,
        file: AssetFiles,
        message: str,
    ) -> None:
        await self.cleanup_s3(file.s3_object_key)

        file.status = FileUploadStatus.FAILED
        file.updated_at = datetime.now(UTC)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        raise AssetFileValidationError(message)

    async def process_s3_upload_event(
        self,
        *,
        object_key: str,
        event_size: int,
    ) -> AssetFiles:
        file = await self.repository.get_by_object_key(object_key)

        if file is None:
            raise AssetFileNotFoundError()

        return await self.confirm_upload(
            asset_id=file.asset_id,
            file_id=file.id,
            allow_terminal_status=True,
            event_size=event_size,
        )

    async def cleanup_expired_pending_uploads(
        self, *, max_age: timedelta = timedelta(hours=24)
    ) -> dict[str, int]:
        cutoff = datetime.now(UTC) - max_age
        expired_files = await self.repository.list_expired_pending(cutoff=cutoff)

        candidates = [(file.id, file.s3_object_key) for file in expired_files]

        cleaned = 0
        failed = 0

        for file_id, object_key in candidates:
            try:
                file = await self.repository.get_by_id(
                    file_id,
                    for_update=True,
                )

                if (
                    file is None
                    or file.status != FileUploadStatus.PENDING
                    or file.deleted_at is not None
                ):
                    continue

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
        """Prepare individual uploads and collect per-file results."""

        upload_results = []
        validated_files = []
        seen_checksums = set()
        seen_filenames = set()

        for file_data in files:
            filename = file_data["filename"]
            filename_key = filename.casefold()

            if filename_key in seen_filenames:
                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "DUPLICATE_FILENAME",
                        "message": f"Duplicate filename in batch: {filename}",
                    }
                )
                continue

            seen_filenames.add(filename_key)

            content_type = file_data["content_type"]
            file_size = file_data["file_size"]
            checksum_sha256 = file_data["checksum_sha256"]

            if (
                not isinstance(checksum_sha256, str)
                or len(checksum_sha256) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in checksum_sha256)
            ):
                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "INVALID_CHECKSUM",
                        "message": f"Invalid SHA-256 checksum for file: {filename}",
                    }
                )
                continue

            checksum_sha256 = checksum_sha256.lower()

            try:
                validate_file(
                    filename,
                    content_type,
                    file_size,
                )
            except ValueError as exc:
                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "INVALID_FILE",
                        "message": str(exc),
                    }
                )
                continue

            if checksum_sha256 in seen_checksums:
                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "DUPLICATE_ASSET_FILE",
                        "message": "This file has a duplicate checksum in the batch",
                    }
                )
                continue

            existing_file = await self.repository.get_by_asset_and_checksum(
                asset_id=asset_id,
                checksum_sha256=checksum_sha256,
            )

            if existing_file is not None:
                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "DUPLICATE_ASSET_FILE",
                        "message": "This file has already been uploaded to this asset",
                    }
                )
                continue

            content_type_enum = FileType(content_type)
            seen_checksums.add(checksum_sha256)

            validated_files.append(
                {
                    "filename": filename,
                    "content_type": content_type_enum,
                    "file_size": file_size,
                    "checksum_sha256": checksum_sha256,
                }
            )

        for file_data in validated_files:
            filename = file_data["filename"]
            object_key = f"assets/{asset_id}/{uuid4()}-{filename}"

            checksum_bytes = bytes.fromhex(file_data["checksum_sha256"])
            checksum_base64 = base64.b64encode(checksum_bytes).decode("ascii")

            try:
                upload_url = self.storage.generate_presigned_put_url(
                    object_key=object_key,
                    content_type=file_data["content_type"].value,
                    checksum_sha256=checksum_base64,
                )
            except Exception:
                logger.exception(
                    "Failed to generate presigned upload URL",
                    extra={
                        "asset_id": str(asset_id),
                        "file_name": filename,
                    },
                )

                upload_results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error_code": "UPLOAD_URL_GENERATION_FAILED",
                        "message": "Failed to generate upload URL for this file",
                    }
                )
                continue

            file = AssetFiles(
                asset_id=asset_id,
                original_file_name=filename,
                content_type=file_data["content_type"],
                file_size=file_data["file_size"],
                checksum_sha256=file_data["checksum_sha256"],
                s3_object_key=object_key,
                status=FileUploadStatus.PENDING,
            )

            try:
                async with self.session.begin_nested():
                    await self.repository.create(file)

            except IntegrityError as exc:
                constraint_name = get_constraint_name(exc)

                if constraint_name == "uq_asset_files_asset_id_checksum_sha256":
                    upload_results.append(
                        {
                            "filename": filename,
                            "status": "failed",
                            "error_code": "DUPLICATE_ASSET_FILE",
                            "message": "This file has already been uploaded to this asset",
                        }
                    )
                    continue

                raise

            upload_results.append(
                {
                    "filename": filename,
                    "file_id": file.id,
                    "status": "pending",
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
        allow_terminal_status: bool = False,
        event_size: int | None = None,
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

        if allow_terminal_status and file.status in {
            FileUploadStatus.FAILED,
            FileUploadStatus.DELETED,
        }:
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

        if event_size is not None and event_size != actual_size:
            await self.reject_upload(
                file=file,
                message="S3 event size does not match actual object size",
            )

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

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(file)

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
                "expires_in": self.storage.GET_URL_EXPIRY_SECONDS,
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

        file = await self.repository.get_by_id(
            file_id,
            for_update=True,
        )

        if file is None or file.asset_id != asset_id:
            raise AssetFileNotFoundError()

        if file.status == FileUploadStatus.DELETED:
            return

        await self.cleanup_s3(file.s3_object_key)

        now = datetime.now(UTC)
        file.status = FileUploadStatus.DELETED
        file.deleted_at = now
        file.updated_at = now

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
