from datetime import date

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.assets import Asset
from app.models.enums import AssetStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_can_get_asset_summary(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    assets = [
        Asset(
            asset_tag="SUM-LAP-001",
            type="laptop",
            serial_number="SN-SUM-1001",
            status=AssetStatus.IN_STOCK,
            purchase_date=date(2026, 9, 8),
        ),
        Asset(
            asset_tag="SUM-LAP-002",
            type="laptop",
            serial_number="SN-SUM-1002",
            status=AssetStatus.IN_STOCK,
            purchase_date=date(2026, 9, 8),
        ),
        Asset(
            asset_tag="SUM-MON-001",
            type="monitor",
            serial_number="SN-SUM-1003",
            status=AssetStatus.ASSIGNED,
            assigned_to=integration_user.id,
            purchase_date=date(2026, 9, 8),
        ),
        Asset(
            asset_tag="SUM-PHN-001",
            type="phone",
            serial_number="SN-SUM-1004",
            status=AssetStatus.REPAIR,
            purchase_date=date(2026, 9, 8),
        ),
        Asset(
            asset_tag="SUM-ACC-001",
            type="accessory",
            serial_number="SN-SUM-1005",
            status=AssetStatus.RETIRED,
            purchase_date=date(2026, 9, 8),
        ),
    ]

    db_session.add_all(assets)
    await db_session.commit()

    response = await integration_client.get(
        "/assets/summary",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data == {
        "total": 5,
        "in_stock": 2,
        "assigned": 1,
        "repair": 1,
        "retired": 1,
    }


@pytest.mark.asyncio
async def test_non_admin_cannot_get_asset_summary(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/assets/summary",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403

    data = response.json()

    assert data["success"] is False
