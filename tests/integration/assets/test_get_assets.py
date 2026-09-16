from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_get_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-GET-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.get(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["id"] == asset_id
    assert data["serial_number"] == "SN-GET-1001"
    assert data["status"] == "in_stock"
    assert data["assigned_to"] is None


@pytest.mark.asyncio
async def test_assigned_user_can_get_own_asset(
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
            "serial_number": "SN-GET-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    result = await db_session.execute(select(Asset).where(Asset.id == UUID(asset_id)))

    asset = result.scalar_one()

    asset.assigned_to = integration_user.id
    asset.status = AssetStatus.ASSIGNED

    await db_session.commit()

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["id"] == asset_id
    assert data["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_user_cannot_get_other_users_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    asset_owner: User,
    db_session,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-GET-1003",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    result = await db_session.execute(select(Asset).where(Asset.id == UUID(asset_id)))

    asset = result.scalar_one()

    asset.assigned_to = asset_owner.id
    asset.status = AssetStatus.ASSIGNED

    await db_session.commit()

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_user_cannot_get_unassigned_asset(
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
            "serial_number": "SN-GET-1004",
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

    response = await integration_client.get(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_nonexistent_asset_returns_404(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets/00000000-0000-0000-0000-000000000001",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_asset_rejects_invalid_id(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    response = await integration_client.get(
        "/assets/not-a-valid-uuid",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 422
