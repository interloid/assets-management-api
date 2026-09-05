from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assets import Asset
from app.models.enums import AssetStatus, AssetType
from tests.integration.conftest import create_test_user


@pytest.mark.asyncio
async def test_create_asset(
    db_session: AsyncSession,
) -> None:
    asset = Asset(
        asset_tag="LAP-001",
        type=AssetType.LAPTOP,
        serial_number="SN-001",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset)
    await db_session.flush()
    await db_session.refresh(asset)

    assert asset.id is not None
    assert asset.asset_tag == "LAP-001"
    assert asset.serial_number == "SN-001"
    assert asset.type == AssetType.LAPTOP
    assert asset.status == AssetStatus.IN_STOCK


@pytest.mark.asyncio
async def test_asset_tag_is_unique(
    db_session: AsyncSession,
) -> None:
    asset1 = Asset(
        asset_tag="LAP-002",
        type=AssetType.LAPTOP,
        serial_number="SN-002",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset1)
    await db_session.flush()

    asset2 = Asset(
        asset_tag="LAP-002",
        type=AssetType.MONITOR,
        serial_number="SN-003",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_asset_serial_number_is_unique(
    db_session: AsyncSession,
) -> None:
    asset1 = Asset(
        asset_tag="LAP-003",
        type=AssetType.LAPTOP,
        serial_number="SN-004",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset1)
    await db_session.flush()

    asset2 = Asset(
        asset_tag="LAP-004",
        type=AssetType.LAPTOP,
        serial_number="SN-004",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_assigned_asset_requires_assigned_user(
    db_session: AsyncSession,
) -> None:
    asset = Asset(
        asset_tag="LAP-005",
        type=AssetType.LAPTOP,
        serial_number="SN-005",
        status=AssetStatus.ASSIGNED,
        assigned_to=None,
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_in_stock_asset_cannot_have_assigned_user(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    asset = Asset(
        asset_tag="LAP-006",
        type=AssetType.LAPTOP,
        serial_number="SN-006",
        status=AssetStatus.IN_STOCK,
        assigned_to=user.id,
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_assigned_asset_with_user_is_valid(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    asset = Asset(
        asset_tag="LAP-007",
        type=AssetType.LAPTOP,
        serial_number="SN-007",
        status=AssetStatus.ASSIGNED,
        assigned_to=user.id,
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset)
    await db_session.flush()

    assert asset.assigned_to == user.id
    assert asset.status == AssetStatus.ASSIGNED


@pytest.mark.asyncio
async def test_asset_cannot_be_assigned_to_nonexistent_user(
    db_session: AsyncSession,
) -> None:
    asset = Asset(
        asset_tag="LAP-008",
        type=AssetType.LAPTOP,
        serial_number="SN-008",
        status=AssetStatus.ASSIGNED,
        assigned_to="00000000-0000-0000-0000-000000000001",
        purchase_date=date(2026, 8, 28),
    )

    db_session.add(asset)

    with pytest.raises(IntegrityError):
        await db_session.flush()
