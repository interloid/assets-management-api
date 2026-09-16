import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_unassign_assigned_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-UNASSIGN-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    assign_response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert assign_response.status_code == 200

    response = await integration_client.post(
        f"/assets/{asset_id}/unassign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["id"] == asset_id
    assert data["data"]["status"] == AssetStatus.IN_STOCK.value
    assert data["data"]["assigned_to"] is None


@pytest.mark.asyncio
async def test_admin_cannot_unassign_non_assigned_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-UNASSIGN-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/unassign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_non_admin_cannot_unassign_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-UNASSIGN-1003",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    assign_response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert assign_response.status_code == 200

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.post(
        f"/assets/{asset_id}/unassign",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unassign_nonexistent_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    from uuid import uuid4

    asset_id = uuid4()

    response = await integration_client.post(
        f"/assets/{asset_id}/unassign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"
