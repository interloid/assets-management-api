import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_delete_in_stock_asset(
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
            "serial_number": "SN-DEL-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_admin_can_delete_retired_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-DEL-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    asset = await db_session.get(Asset, asset_id)
    assert asset is not None

    asset.status = AssetStatus.RETIRED
    await db_session.commit()

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_admin_cannot_delete_assigned_asset(
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
            "serial_number": "SN-DEL-1003",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    asset = await db_session.get(Asset, asset_id)
    assert asset is not None

    asset.status = AssetStatus.ASSIGNED
    asset.assigned_to = integration_user.id

    await db_session.commit()

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_DELETE_CONFLICT"


@pytest.mark.asyncio
async def test_admin_cannot_delete_repair_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
) -> None:
    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-DEL-1004",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    asset = await db_session.get(Asset, asset_id)
    assert asset is not None

    asset.status = AssetStatus.REPAIR
    await db_session.commit()

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_DELETE_CONFLICT"


@pytest.mark.asyncio
async def test_delete_nonexistent_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    from uuid import uuid4

    asset_id = uuid4()

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_asset(
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
            "serial_number": "SN-DEL-1005",
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

    response = await integration_client.delete(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403
