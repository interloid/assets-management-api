from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.modules.user.models import User
from app.shared.models.enums import FileType, FileUploadStatus


def user_token(user: User) -> str:
    return create_access_token(
        user_id=str(user.id),
        role=user.role.value,
        token_version=user.token_version,
        family_id=str(uuid4()),
    )


def mock_uploaded_file(asset_id):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        original_file_name="report.pdf",
        content_type=FileType.PDF,
        file_size=1024,
        status=FileUploadStatus.UPLOADED,
        uploaded_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_presign_upload_returns_created_response(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    asset_id = uuid4()
    file_id = uuid4()

    service = MagicMock()
    service.create_upload = AsyncMock(
        return_value={
            "file_id": file_id,
            "upload_url": "https://example.test/upload",
            "expires_in": 300,
        }
    )

    with patch(
        "app.api.v1.endpoints.asset_files.AssetFileService",
        return_value=service,
    ):
        integration_client.cookies.set("access_token", admin_access_token)
        response = await integration_client.post(
            f"/api/v1/assets/{asset_id}/files/presign",
            json={
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "file_size": 1024,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_id"] == str(file_id)
    assert body["data"]["upload_url"] == "https://example.test/upload"
    assert body["data"]["expires_in"] == 300
    service.create_upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_presign_upload_rejects_invalid_payload(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/files/presign",
        json={
            "filename": "report.exe",
            "content_type": "application/x-msdownload",
            "file_size": -1,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_presign_upload(
    integration_client: AsyncClient,
    integration_user: User,
):
    integration_client.cookies.set("access_token", user_token(integration_user))

    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/files/presign",
        json={
            "filename": "report.pdf",
            "content_type": "application/pdf",
            "file_size": 1024,
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_confirm_upload_returns_success_response(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    asset_id = uuid4()
    file_id = uuid4()
    file = mock_uploaded_file(asset_id)

    service = MagicMock()
    service.confirm_upload = AsyncMock(return_value=file)

    with patch(
        "app.api.v1.endpoints.asset_files.AssetFileService",
        return_value=service,
    ):
        integration_client.cookies.set("access_token", admin_access_token)
        response = await integration_client.post(
            f"/api/v1/assets/{asset_id}/files/{file_id}/confirm"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_id"] == str(file.id)
    assert body["data"]["asset_id"] == str(asset_id)
    service.confirm_upload.assert_awaited_once_with(
        asset_id=asset_id,
        file_id=file_id,
    )


@pytest.mark.asyncio
async def test_non_admin_cannot_confirm_upload(
    integration_client: AsyncClient,
    integration_user: User,
):
    integration_client.cookies.set("access_token", user_token(integration_user))

    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/files/{uuid4()}/confirm"
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_files_returns_download_urls(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    asset_id = uuid4()
    file = mock_uploaded_file(asset_id)
    file_dict = {
        "file_id": file.id,
        "asset_id": file.asset_id,
        "original_file_name": file.original_file_name,
        "content_type": file.content_type.value,
        "file_size": file.file_size,
        "status": file.status.value,
        "uploaded_at": file.uploaded_at,
        "download_url": "https://example.test/download",
        "expires_in": 900,
    }

    service = MagicMock()
    service.list_files = AsyncMock(return_value=[file_dict])

    with patch(
        "app.api.v1.endpoints.asset_files.AssetFileService",
        return_value=service,
    ):
        integration_client.cookies.set("access_token", admin_access_token)
        response = await integration_client.get(f"/api/v1/assets/{asset_id}/files")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["download_url"] == "https://example.test/download"
    assert body["data"][0]["expires_in"] == 900
    service.list_files.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_files_rejects_unauthenticated_request(
    integration_client: AsyncClient,
):
    integration_client.cookies.delete("access_token")

    response = await integration_client.get(f"/api/v1/assets/{uuid4()}/files")

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_delete_file_returns_no_content(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    asset_id = uuid4()
    file_id = uuid4()

    service = MagicMock()
    service.delete_file = AsyncMock(return_value=None)

    with patch(
        "app.api.v1.endpoints.asset_files.AssetFileService",
        return_value=service,
    ):
        integration_client.cookies.set("access_token", admin_access_token)
        response = await integration_client.delete(
            f"/api/v1/assets/{asset_id}/files/{file_id}"
        )

    assert response.status_code == 204
    assert response.content == b""
    service.delete_file.assert_awaited_once_with(
        asset_id=asset_id,
        file_id=file_id,
    )


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_file(
    integration_client: AsyncClient,
    integration_user: User,
):
    integration_client.cookies.set("access_token", user_token(integration_user))

    response = await integration_client.delete(
        f"/api/v1/assets/{uuid4()}/files/{uuid4()}"
    )

    assert response.status_code == 403
