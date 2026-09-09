import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_update_asset(
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
            "serial_number": "SN-UPD-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.patch(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "notes": "Updated notes",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["id"] == asset_id
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_update_asset_type_generates_new_asset_tag(
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
            "serial_number": "SN-UPD-1002",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    created_data = create_response.json()["data"]
    asset_id = created_data["id"]
    old_asset_tag = created_data["asset_tag"]

    response = await integration_client.patch(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["type"] == "monitor"
    assert data["asset_tag"] != old_asset_tag
    assert data["asset_tag"].startswith("IL-MON-")


@pytest.mark.asyncio
async def test_update_asset_with_same_type_keeps_asset_tag(
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
            "serial_number": "SN-UPD-1003",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    created_data = create_response.json()["data"]
    asset_id = created_data["id"]
    old_asset_tag = created_data["asset_tag"]

    response = await integration_client.patch(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["type"] == "laptop"
    assert data["asset_tag"] == old_asset_tag


@pytest.mark.asyncio
async def test_update_asset_rejects_duplicate_serial_number(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    first_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-UPD-1004",
            "purchase_date": "2026-09-08",
        },
    )

    assert first_response.status_code == 201

    _first_asset_id = first_response.json()["data"]["id"]

    second_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-UPD-1005",
            "purchase_date": "2026-09-08",
        },
    )

    assert second_response.status_code == 201

    second_asset_id = second_response.json()["data"]["id"]

    response = await integration_client.patch(
        f"/assets/{second_asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "serial_number": "SN-UPD-1004",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "SERIAL_NUMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_asset_rejects_asset_tag(
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
            "serial_number": "SN-UPD-1006",
            "purchase_date": "2026-09-08",
        },
    )

    assert create_response.status_code == 201

    asset_id = create_response.json()["data"]["id"]

    response = await integration_client.patch(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "asset_tag": "IL-LAP-9999",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_update_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    from app.core.security import create_access_token

    create_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-UPD-1007",
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

    response = await integration_client.patch(
        f"/assets/{asset_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "notes": "Unauthorized update",
        },
    )

    assert response.status_code == 403
