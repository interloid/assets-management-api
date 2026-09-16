import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_create_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-ABC-1001",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    data = response.json()["data"]

    assert data["asset_tag"] == "IL-LAP-0001"
    assert data["status"] == "in_stock"
    assert data["assigned_to"] is None


@pytest.mark.asyncio
async def test_create_asset_rejects_assigned_to(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-1002",
            "purchase_date": "2026-09-08",
            "assigned_to": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_asset_rejects_duplicate_serial_number(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    payload = {
        "type": "laptop",
        "serial_number": "SN-ABC-1003",
        "purchase_date": "2026-09-08",
    }

    first_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json=payload,
    )

    assert second_response.status_code == 409

    data = second_response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "SERIAL_NUMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_non_admin_cannot_create_asset(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    from app.core.security import create_access_token

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-1004",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_asset_rejects_invalid_payload(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "invalid_type",
            "serial_number": "",
        },
    )

    assert response.status_code == 422
