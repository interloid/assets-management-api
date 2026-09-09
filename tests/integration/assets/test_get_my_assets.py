from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_user_can_list_my_assets(
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
            "serial_number": "SN-MY-001",
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

    user_access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets/my",
        headers={
            "Authorization": f"Bearer {user_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["page"] == 1
    assert data["size"] == 20
    assert data["total"] == 1
    assert data["pages"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["serial_number"] == "SN-MY-001"
    assert data["items"][0]["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_my_assets_returns_only_assets_assigned_to_current_user(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    integration_admin: User,
    db_session,
) -> None:
    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-MY-USER",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    user_asset_id = response.json()["data"]["id"]

    result = await db_session.execute(
        select(Asset).where(Asset.id == UUID(user_asset_id))
    )

    user_asset = result.scalar_one()
    user_asset.assigned_to = integration_user.id
    user_asset.status = AssetStatus.ASSIGNED

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-MY-OTHER",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    other_asset_id = response.json()["data"]["id"]

    result = await db_session.execute(
        select(Asset).where(Asset.id == UUID(other_asset_id))
    )

    other_asset = result.scalar_one()
    other_asset.assigned_to = integration_admin.id
    other_asset.status = AssetStatus.ASSIGNED

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "phone",
            "serial_number": "SN-MY-UNASSIGNED",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    await db_session.commit()

    user_access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets/my",
        headers={
            "Authorization": f"Bearer {user_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["serial_number"] == "SN-MY-USER"
    assert data["items"][0]["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_my_assets_supports_pagination(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    asset_ids = []

    for index in range(5):
        response = await integration_client.post(
            "/assets",
            headers={
                "Authorization": f"Bearer {admin_access_token}",
            },
            json={
                "type": "laptop",
                "serial_number": f"SN-MY-PAGE-{index}",
                "purchase_date": "2026-09-08",
            },
        )

        assert response.status_code == 201

        asset_ids.append(response.json()["data"]["id"])

    result = await db_session.execute(
        select(Asset).where(Asset.id.in_([UUID(asset_id) for asset_id in asset_ids]))
    )

    assets = result.scalars().all()

    for asset in assets:
        asset.assigned_to = integration_user.id
        asset.status = AssetStatus.ASSIGNED

    await db_session.commit()

    user_access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets/my?page=2&size=2",
        headers={
            "Authorization": f"Bearer {user_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["page"] == 2
    assert data["size"] == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_my_assets_requires_authentication(
    integration_client: AsyncClient,
) -> None:
    response = await integration_client.get("/assets/my")

    assert response.status_code == 401
