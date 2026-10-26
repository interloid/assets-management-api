from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.asset.exceptions import AssetNotFoundError
from app.modules.asset_files.exceptions import (
    AssetFileNotFoundError,
    AssetFileValidationError,
)
from app.modules.asset_files.models import AssetFiles
from app.modules.asset_files.service import AssetFileService
from app.modules.auth.exceptions import AuthorizationError
from app.shared.models.enums import FileType, FileUploadStatus, UserRole


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def storage():
    mock = MagicMock()
    mock.PUT_URL_EXPIRY_SECONDS = 300
    mock.GET_URL_EXPIRY_SECONDS = 900
    mock.generate_presigned_put_url.return_value = "https://example.test/upload"
    mock.generate_presigned_get_url.return_value = "https://example.test/download"
    return mock


@pytest.fixture
def service(session, storage):
    instance = AssetFileService(session=session, storage=storage)
    instance.asset_repository = AsyncMock()
    instance.repository = AsyncMock()
    return instance


@pytest.fixture
def asset():
    return SimpleNamespace(
        id=uuid4(),
        assigned_to=uuid4(),
    )


@pytest.fixture
def pending_file(asset):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset.id,
        original_file_name="report.pdf",
        content_type=FileType.PDF,
        file_size=1024,
        s3_object_key=f"assets/{asset.id}/test-report.pdf",
        status=FileUploadStatus.PENDING,
        uploaded_at=None,
        deleted_at=None,
    )


@pytest.mark.asyncio
async def test_create_upload_success(service, asset, storage):
    service.asset_repository.get_by_id.return_value = asset

    result = await service.create_upload(
        asset_id=asset.id,
        filename="report.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    created_file = service.repository.create.await_args.args[0]

    assert isinstance(created_file, AssetFiles)
    assert created_file.asset_id == asset.id
    assert created_file.original_file_name == "report.pdf"
    assert created_file.content_type == FileType.PDF
    assert created_file.file_size == 1024
    assert created_file.status == FileUploadStatus.PENDING
    assert created_file.s3_object_key.startswith(f"assets/{asset.id}/")

    storage.generate_presigned_put_url.assert_called_once_with(
        object_key=created_file.s3_object_key,
        content_type=FileType.PDF,
    )
    service.session.commit.assert_awaited_once()
    assert result["upload_url"] == "https://example.test/upload"
    assert result["expires_in"] == 300


@pytest.mark.asyncio
async def test_create_upload_rejects_missing_asset(service, asset):
    service.asset_repository.get_by_id.return_value = None

    with pytest.raises(AssetNotFoundError):
        await service.create_upload(
            asset_id=asset.id,
            filename="report.pdf",
            content_type="application/pdf",
            file_size=1024,
        )

    service.repository.create.assert_not_awaited()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_upload_rejects_invalid_file_type(service, asset, storage):
    service.asset_repository.get_by_id.return_value = asset

    with pytest.raises(AssetFileValidationError):
        await service.create_upload(
            asset_id=asset.id,
            filename="program.exe",
            content_type="application/octet-stream",
            file_size=1024,
        )

    service.repository.create.assert_not_awaited()
    service.session.commit.assert_not_awaited()
    storage.generate_presigned_put_url.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_upload_success(service, asset, pending_file, storage):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file
    storage.get_object_metadata.return_value = {
        "content_type": "application/pdf",
        "content_length": pending_file.file_size,
        "etag": '"test-etag"',
        "last_modified": None,
        "metadata": {},
    }

    result = await service.confirm_upload(
        asset_id=asset.id,
        file_id=pending_file.id,
    )

    assert result is pending_file
    assert result.status == FileUploadStatus.UPLOADED
    assert result.uploaded_at is not None
    service.session.commit.assert_awaited_once()
    service.session.refresh.assert_awaited_once_with(pending_file)
    storage.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_upload_rejects_missing_s3_object(
    service, asset, pending_file, storage
):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file
    storage.get_object_metadata.return_value = None

    with pytest.raises(AssetFileValidationError):
        await service.confirm_upload(
            asset_id=asset.id,
            file_id=pending_file.id,
        )

    assert pending_file.status == FileUploadStatus.FAILED
    service.session.commit.assert_awaited_once()
    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)


@pytest.mark.asyncio
async def test_confirm_upload_rejects_file_size_mismatch(
    service, asset, pending_file, storage
):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file
    storage.get_object_metadata.return_value = {
        "content_type": "application/pdf",
        "content_length": pending_file.file_size + 1,
        "etag": '"test-etag"',
        "last_modified": None,
        "metadata": {},
    }

    with pytest.raises(AssetFileValidationError):
        await service.confirm_upload(
            asset_id=asset.id,
            file_id=pending_file.id,
        )

    assert pending_file.status == FileUploadStatus.FAILED
    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)


@pytest.mark.asyncio
async def test_confirm_upload_rejects_file_belonging_to_another_asset(
    service, asset, pending_file
):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file

    with pytest.raises(AssetFileNotFoundError):
        await service.confirm_upload(
            asset_id=uuid4(),
            file_id=pending_file.id,
        )

    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_expired_pending_uploads_success(
    service, session, storage, asset, pending_file
):
    service.repository.list_expired_pending.return_value = [pending_file]
    service.repository.get_by_id.return_value = pending_file

    result = await service.cleanup_expired_pending_uploads()

    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)
    service.repository.get_by_id.assert_awaited_once_with(pending_file.id)

    assert pending_file.status == FileUploadStatus.DELETED
    assert pending_file.deleted_at is not None
    assert pending_file.updated_at is not None

    session.commit.assert_awaited_once()
    assert result == {"found": 1, "cleaned": 1, "failed": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "deleted_at"),
    [
        (FileUploadStatus.UPLOADED, None),
        (FileUploadStatus.DELETED, None),
        (FileUploadStatus.PENDING, "already-deleted"),
    ],
)
async def test_cleanup_expired_pending_uploads_skips_ineligible_records(
    service, session, storage, pending_file, status, deleted_at
):
    pending_file.status = status
    pending_file.deleted_at = deleted_at

    service.repository.list_expired_pending.return_value = [pending_file]
    service.repository.get_by_id.return_value = pending_file

    result = await service.cleanup_expired_pending_uploads()

    storage.delete_object.assert_not_called()
    session.commit.assert_not_awaited()
    assert result == {"found": 1, "cleaned": 0, "failed": 0}


@pytest.mark.asyncio
async def test_cleanup_expired_pending_uploads_skips_missing_record(
    service, session, storage, pending_file
):
    service.repository.list_expired_pending.return_value = [pending_file]
    service.repository.get_by_id.return_value = None

    result = await service.cleanup_expired_pending_uploads()

    storage.delete_object.assert_not_called()
    session.commit.assert_not_awaited()
    assert result == {"found": 1, "cleaned": 0, "failed": 0}


@pytest.mark.asyncio
async def test_cleanup_expired_pending_uploads_handles_s3_failure(
    service, session, storage, pending_file
):
    service.repository.list_expired_pending.return_value = [pending_file]
    service.repository.get_by_id.return_value = pending_file
    storage.delete_object.side_effect = RuntimeError("S3 deletion failed")

    result = await service.cleanup_expired_pending_uploads()

    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    assert result == {"found": 1, "cleaned": 0, "failed": 1}


@pytest.mark.asyncio
async def test_cleanup_expired_pending_uploads_handles_commit_failure(
    service, session, storage, pending_file
):
    service.repository.list_expired_pending.return_value = [pending_file]
    service.repository.get_by_id.return_value = pending_file
    session.commit.side_effect = RuntimeError("Database commit failed")

    result = await service.cleanup_expired_pending_uploads()

    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)
    assert pending_file.status == FileUploadStatus.DELETED
    session.rollback.assert_awaited_once()
    assert result == {"found": 1, "cleaned": 0, "failed": 1}


@pytest.mark.asyncio
async def test_list_files_admin_success(service, storage, asset, pending_file):
    asset.assigned_to = uuid4()
    admin = SimpleNamespace(id=uuid4(), role=UserRole.ADMIN)

    pending_file.status = FileUploadStatus.UPLOADED
    pending_file.uploaded_at = datetime.now(timezone.utc)

    service.asset_repository.get_by_id.return_value = asset
    service.repository.list_uploaded_for_asset.return_value = [pending_file]

    result = await service.list_files(
        asset_id=asset.id,
        current_user=admin,
    )

    assert len(result) == 1
    assert result[0]["file_id"] == pending_file.id
    assert result[0]["asset_id"] == asset.id
    assert result[0]["original_file_name"] == "report.pdf"
    assert result[0]["content_type"] == FileType.PDF.value
    assert result[0]["status"] == FileUploadStatus.UPLOADED.value
    assert result[0]["download_url"] == "https://example.test/download"
    assert result[0]["expires_in"] == 900

    storage.generate_presigned_get_url.assert_called_once_with(
        pending_file.s3_object_key
    )


@pytest.mark.asyncio
async def test_list_files_assigned_user_success(service, asset, pending_file):
    user = SimpleNamespace(id=asset.assigned_to, role=UserRole.USER)

    pending_file.status = FileUploadStatus.UPLOADED
    service.asset_repository.get_by_id.return_value = asset
    service.repository.list_uploaded_for_asset.return_value = [pending_file]

    result = await service.list_files(
        asset_id=asset.id,
        current_user=user,
    )

    assert len(result) == 1
    service.repository.list_uploaded_for_asset.assert_awaited_once_with(asset.id)


@pytest.mark.asyncio
async def test_list_files_rejects_unassigned_user(service, asset, storage):
    user = SimpleNamespace(id=uuid4(), role=UserRole.USER)
    service.asset_repository.get_by_id.return_value = asset

    with pytest.raises(AuthorizationError):
        await service.list_files(
            asset_id=asset.id,
            current_user=user,
        )

    service.repository.list_uploaded_for_asset.assert_not_awaited()
    storage.generate_presigned_get_url.assert_not_called()


@pytest.mark.asyncio
async def test_list_files_rejects_missing_asset(service, asset):
    user = SimpleNamespace(id=asset.assigned_to, role=UserRole.USER)
    service.asset_repository.get_by_id.return_value = None

    with pytest.raises(AssetNotFoundError):
        await service.list_files(
            asset_id=asset.id,
            current_user=user,
        )

    service.repository.list_uploaded_for_asset.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_file_success(service, session, storage, asset, pending_file):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file

    await service.delete_file(
        asset_id=asset.id,
        file_id=pending_file.id,
    )

    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)
    assert pending_file.status == FileUploadStatus.DELETED
    assert pending_file.deleted_at is not None
    assert pending_file.updated_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_file_rejects_missing_asset(service, pending_file):
    service.asset_repository.get_by_id.return_value = None

    with pytest.raises(AssetNotFoundError):
        await service.delete_file(
            asset_id=pending_file.asset_id,
            file_id=pending_file.id,
        )


@pytest.mark.asyncio
async def test_delete_file_rejects_missing_file(service, asset):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = None

    with pytest.raises(AssetFileNotFoundError):
        await service.delete_file(
            asset_id=asset.id,
            file_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_delete_file_rejects_file_from_another_asset(
    service, asset, pending_file, storage
):
    service.asset_repository.get_by_id.return_value = asset
    pending_file.asset_id = uuid4()
    service.repository.get_by_id.return_value = pending_file

    with pytest.raises(AssetFileNotFoundError):
        await service.delete_file(
            asset_id=asset.id,
            file_id=pending_file.id,
        )

    storage.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_delete_file_is_idempotent_when_already_deleted(
    service, session, storage, asset, pending_file
):
    pending_file.status = FileUploadStatus.DELETED
    pending_file.deleted_at = datetime.now(timezone.utc)

    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file

    await service.delete_file(
        asset_id=asset.id,
        file_id=pending_file.id,
    )

    storage.delete_object.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_file_rolls_back_on_commit_failure(
    service, session, storage, asset, pending_file
):
    service.asset_repository.get_by_id.return_value = asset
    service.repository.get_by_id.return_value = pending_file
    session.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        await service.delete_file(
            asset_id=asset.id,
            file_id=pending_file.id,
        )

    storage.delete_object.assert_called_once_with(pending_file.s3_object_key)
    session.rollback.assert_awaited_once()
