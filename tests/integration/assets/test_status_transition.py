import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_change_in_stock_asset_to_repair(
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
            "serial_number": "SN-STATUS-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "repair",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "repair"


@pytest.mark.asyncio
async def test_admin_can_change_in_stock_asset_to_retired(
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
            "serial_number": "SN-STATUS-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "retired",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "retired"


@pytest.mark.asyncio
async def test_admin_can_change_assigned_asset_to_repair(
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
            "serial_number": "SN-STATUS-1003",
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

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "repair",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "repair"

    await db_session.refresh(asset)

    assert asset.status == AssetStatus.REPAIR
    assert asset.assigned_to is None


@pytest.mark.asyncio
async def test_admin_can_change_repair_asset_to_in_stock(
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
            "type": "phone",
            "serial_number": "SN-STATUS-1004",
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
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "in_stock",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "in_stock"


@pytest.mark.asyncio
async def test_admin_can_change_repair_asset_to_retired(
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
            "type": "accessory",
            "serial_number": "SN-STATUS-1005",
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
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "retired",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "retired"


@pytest.mark.asyncio
async def test_admin_cannot_change_in_stock_to_assigned_via_status(
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
            "serial_number": "SN-STATUS-1006",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "assigned",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_admin_cannot_change_assigned_to_in_stock_via_status(
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
            "serial_number": "SN-STATUS-1007",
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

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "in_stock",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_admin_cannot_change_retired_asset_status(
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
            "serial_number": "SN-STATUS-1008",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    asset = await db_session.get(Asset, asset_id)
    assert asset is not None

    asset.status = AssetStatus.RETIRED
    await db_session.commit()

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "repair",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_change_status_nonexistent_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    from uuid import uuid4

    asset_id = uuid4()

    response = await integration_client.post(
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "status": "repair",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_non_admin_cannot_change_asset_status(
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
            "serial_number": "SN-STATUS-1009",
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
        f"/assets/{asset_id}/status",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "status": "repair",
        },
    )

    assert response.status_code == 403
