import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_assign_in_stock_asset(
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
            "serial_number": "SN-ASSIGN-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["id"] == asset_id
    assert data["data"]["status"] == AssetStatus.ASSIGNED.value
    assert data["data"]["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_admin_cannot_assign_non_in_stock_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-ASSIGN-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    asset = await db_session.get(Asset, asset_id)
    assert asset is not None

    asset.status = AssetStatus.REPAIR
    await db_session.commit()

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_assign_fails_when_user_does_not_exist(
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
            "serial_number": "SN-ASSIGN-1003",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_ASSIGNMENT_USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_assign_fails_when_user_is_inactive(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    integration_user.is_active = False
    await db_session.commit()

    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-ASSIGN-1004",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_ASSIGNMENT_USER_INACTIVE"


@pytest.mark.asyncio
async def test_non_admin_cannot_assign_asset(
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
            "serial_number": "SN-ASSIGN-1005",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_assign_nonexistent_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    from uuid import uuid4

    asset_id = uuid4()

    response = await integration_client.post(
        f"/assets/{asset_id}/assign",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"
