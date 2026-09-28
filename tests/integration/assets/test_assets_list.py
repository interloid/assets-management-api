import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_list_assets(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    for serial_number in ["SN-LIST-1001", "SN-LIST-1002", "SN-LIST-1003"]:
        response = await integration_client.post(
            "/assets",
            headers={
                "Authorization": f"Bearer {admin_access_token}",
            },
            json={
                "type": "laptop",
                "serial_number": serial_number,
                "purchase_date": "2026-09-08",
            },
        )

        assert response.status_code == 201

    response = await integration_client.get(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["page"] == 1
    assert meta["size"] == 20
    assert meta["total_items"] == 3
    assert meta["total_pages"] == 1
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_assets_pagination(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    for index in range(5):
        response = await integration_client.post(
            "/assets",
            headers={
                "Authorization": f"Bearer {admin_access_token}",
            },
            json={
                "type": "laptop",
                "serial_number": f"SN-PAGE-{index}",
                "purchase_date": "2026-09-08",
            },
        )

        assert response.status_code == 201

    response = await integration_client.get(
        "/assets?page=2&size=2",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["page"] == 2
    assert meta["size"] == 2
    assert meta["total_items"] == 5
    assert meta["total_pages"] == 3
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_assets_filters_by_type(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    laptop_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-FILTER-LAPTOP",
            "purchase_date": "2026-09-08",
        },
    )

    assert laptop_response.status_code == 201

    monitor_response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-FILTER-MONITOR",
            "purchase_date": "2026-09-08",
        },
    )

    assert monitor_response.status_code == 201

    response = await integration_client.get(
        "/assets?type=laptop",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["total_items"] == 1
    assert meta["total_pages"] == 1
    assert len(data) == 1
    assert data[0]["type"] == "laptop"
    assert data[0]["serial_number"] == "SN-FILTER-LAPTOP"


@pytest.mark.asyncio
async def test_list_assets_filters_by_status(
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
            "serial_number": "SN-STATUS-001",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    response = await integration_client.get(
        "/assets?asset_status=in_stock",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["total_items"] == 1
    assert meta["total_pages"] == 1
    assert len(data) == 1
    assert data[0]["status"] == "in_stock"


@pytest.mark.asyncio
async def test_list_assets_search(
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
            "serial_number": "SEARCH-SN-001",
            "purchase_date": "2026-09-08",
            "notes": "Dell development laptop",
        },
    )

    assert response.status_code == 201

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "NORMAL-SN-002",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 201

    response = await integration_client.get(
        "/assets?search=dell",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["total_items"] == 1
    assert meta["total_pages"] == 1
    assert len(data) == 1
    assert data[0]["serial_number"] == "SEARCH-SN-001"


@pytest.mark.asyncio
async def test_list_assets_filters_combine_with_and(
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
            "serial_number": "SN-AND-001",
            "purchase_date": "2026-09-08",
            "notes": "Development laptop",
        },
    )

    assert response.status_code == 201

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "monitor",
            "serial_number": "SN-AND-002",
            "purchase_date": "2026-09-08",
            "notes": "Development monitor",
        },
    )

    assert response.status_code == 201

    response = await integration_client.get(
        "/assets?type=laptop&asset_status=in_stock&search=development",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["total_items"] == 1
    assert meta["total_pages"] == 1
    assert len(data) == 1
    assert data[0]["serial_number"] == "SN-AND-001"


@pytest.mark.asyncio
async def test_list_assets_filters_by_warranty_expiry(
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
            "serial_number": "SN-WARRANTY-001",
            "purchase_date": "2026-09-08",
            "warranty_expiry": "2026-10-01",
        },
    )

    assert response.status_code == 201

    response = await integration_client.post(
        "/assets",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
        json={
            "type": "laptop",
            "serial_number": "SN-WARRANTY-002",
            "purchase_date": "2026-09-08",
            "warranty_expiry": "2027-01-01",
        },
    )

    assert response.status_code == 201

    response = await integration_client.get(
        "/assets?warranty_expiring_before=2026-12-31",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    meta = body["meta"]

    assert meta["total_items"] == 1
    assert meta["total_pages"] == 1
    assert len(data) == 1
    assert data[0]["serial_number"] == "SN-WARRANTY-001"


@pytest.mark.asyncio
async def test_non_admin_cannot_list_assets(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    from app.core.security import create_access_token

    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_assets_rejects_invalid_query_parameters(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    response = await integration_client.get(
        "/assets?page=0",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 422

    response = await integration_client.get(
        "/assets?size=101",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 422

    response = await integration_client.get(
        "/assets?sort=updated_at",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 422
