from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from uuid6 import uuid7

from app.exceptions.assets import (
    AssetAssignmentUserInactiveError,
    AssetAssignmentUserNotFoundError,
    AssetDeleteConflictError,
    AssetNotFoundError,
    InvalidAssetStatusTransitionError,
)
from app.models.assets import Asset
from app.models.enums import AssetStatus, AssetType, UserRole
from app.services.assets import AssetService


@pytest.mark.asyncio
async def test_list_assets(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    now = datetime.now(timezone.utc)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
        warranty_expiry=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )

    service.asset_repository.list = AsyncMock(
        return_value=([asset], 1),
    )

    result = await service.list(
        page=1,
        size=20,
    )

    service.asset_repository.list.assert_awaited_once_with(
        page=1,
        size=20,
        asset_type=None,
        asset_status=None,
        assigned_to=None,
        warranty_expiring_before=None,
        search=None,
        sort="created_at",
        order="desc",
    )

    assert result.total == 1
    assert result.page == 1
    assert result.size == 20
    assert result.pages == 1
    assert len(result.items) == 1
    assert result.items[0].asset_tag == "IL-LAP-0001"


@pytest.mark.asyncio
async def test_list_assets_calculates_pages(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    now = datetime.now(timezone.utc)

    assets = [
        Asset(
            id=uuid7(),
            asset_tag=f"IL-LAP-000{i}",
            type=AssetType.LAPTOP,
            serial_number=f"ABC1234{i}",
            status=AssetStatus.IN_STOCK,
            purchase_date=date(2026, 1, 1),
            warranty_expiry=None,
            notes=None,
            created_at=now,
            updated_at=now,
        )
        for i in range(1, 3)
    ]

    service.asset_repository.list = AsyncMock(
        return_value=(assets, 25),
    )

    result = await service.list(
        page=2,
        size=10,
    )

    assert result.total == 25
    assert result.page == 2
    assert result.size == 10
    assert result.pages == 3


@pytest.mark.asyncio
async def test_list_assets_empty_result(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    service.asset_repository.list = AsyncMock(
        return_value=([], 0),
    )

    result = await service.list(
        page=1,
        size=20,
    )

    assert result.items == []
    assert result.total == 0
    assert result.page == 1
    assert result.size == 20
    assert result.pages == 0


@pytest.mark.asyncio
async def test_get_by_id_for_admin(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    created_user.role = UserRole.ADMIN

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )

    result = await service.get_by_id(
        asset_id=asset.id,
        current_user=created_user,
    )

    service.asset_repository.get_by_id.assert_awaited_once_with(
        asset.id,
    )

    assert result is asset


@pytest.mark.asyncio
async def test_get_by_id_for_assigned_user(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.ASSIGNED,
        assigned_to=created_user.id,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )

    result = await service.get_by_id(
        asset_id=asset.id,
        current_user=created_user,
    )

    assert result is asset


@pytest.mark.asyncio
async def test_get_by_id_raises_when_asset_not_found(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    service.asset_repository.get_by_id = AsyncMock(
        return_value=None,
    )
    asset_id = uuid7()
    with pytest.raises(AssetNotFoundError):
        await service.get_by_id(
            asset_id=asset_id,
            current_user=created_user,
        )


@pytest.mark.asyncio
async def test_get_by_id_raises_when_user_is_not_allowed(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.ASSIGNED,
        assigned_to=uuid7(),
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )

    with pytest.raises(AssetNotFoundError):
        await service.get_by_id(
            asset_id=asset.id,
            current_user=created_user,
        )


@pytest.mark.asyncio
async def test_delete_asset(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.delete = AsyncMock()

    await service.delete(asset.id)

    service.asset_repository.get_by_id.assert_awaited_once_with(
        asset.id,
    )
    service.asset_repository.delete.assert_awaited_once_with(
        asset,
    )
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        AssetStatus.ASSIGNED,
        AssetStatus.REPAIR,
    ],
)
async def test_delete_asset_rejects_invalid_status(
    mock_session,
    status,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=status,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.delete = AsyncMock()

    with pytest.raises(AssetDeleteConflictError):
        await service.delete(asset.id)

    service.asset_repository.delete.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_asset(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.user_repository.get_by_id = AsyncMock(
        return_value=created_user,
    )
    service.asset_repository.assign = AsyncMock()

    result = await service.assign(
        asset_id=asset.id,
        user_id=created_user.id,
    )

    service.user_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )
    service.asset_repository.assign.assert_awaited_once_with(
        asset,
        created_user.id,
    )
    mock_session.commit.assert_awaited_once()

    assert result is asset


@pytest.mark.asyncio
async def test_assign_asset_user_not_found(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.user_repository.get_by_id = AsyncMock(
        return_value=None,
    )
    service.asset_repository.assign = AsyncMock()

    user_id = uuid7()
    with pytest.raises(AssetAssignmentUserNotFoundError):
        await service.assign(
            asset_id=asset.id,
            user_id=user_id,
        )

    service.asset_repository.assign.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_asset_user_inactive(
    mock_session,
    inactive_user,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.user_repository.get_by_id = AsyncMock(
        return_value=inactive_user,
    )
    service.asset_repository.assign = AsyncMock()

    with pytest.raises(AssetAssignmentUserInactiveError):
        await service.assign(
            asset_id=asset.id,
            user_id=inactive_user.id,
        )

    service.asset_repository.assign.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_asset_rejects_invalid_transition(
    mock_session,
    created_user,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.RETIRED,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.user_repository.get_by_id = AsyncMock()
    service.asset_repository.assign = AsyncMock()

    with pytest.raises(InvalidAssetStatusTransitionError):
        await service.assign(
            asset_id=asset.id,
            user_id=created_user.id,
        )

    service.user_repository.get_by_id.assert_not_awaited()
    service.asset_repository.assign.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unassign_asset(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.ASSIGNED,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.unassign = AsyncMock()

    result = await service.unassign(asset.id)

    service.asset_repository.unassign.assert_awaited_once_with(
        asset,
    )
    mock_session.commit.assert_awaited_once()

    assert result is asset


@pytest.mark.asyncio
async def test_unassign_asset_rejects_invalid_transition(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.unassign = AsyncMock()

    with pytest.raises(InvalidAssetStatusTransitionError):
        await service.unassign(asset.id)

    service.asset_repository.unassign.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_status(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.change_status = AsyncMock()

    result = await service.change_status(
        asset_id=asset.id,
        new_status=AssetStatus.REPAIR,
    )

    service.asset_repository.change_status.assert_awaited_once_with(
        asset=asset,
        new_status=AssetStatus.REPAIR,
    )
    mock_session.commit.assert_awaited_once()

    assert result is asset


@pytest.mark.asyncio
async def test_change_status_rejects_assignment_transition(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    asset = Asset(
        id=uuid7(),
        asset_tag="IL-LAP-0001",
        type=AssetType.LAPTOP,
        serial_number="ABC12345",
        status=AssetStatus.IN_STOCK,
        purchase_date=date(2026, 1, 1),
    )

    service.asset_repository.get_by_id = AsyncMock(
        return_value=asset,
    )
    service.asset_repository.change_status = AsyncMock()

    with pytest.raises(InvalidAssetStatusTransitionError):
        await service.change_status(
            asset_id=asset.id,
            new_status=AssetStatus.ASSIGNED,
        )

    service.asset_repository.change_status.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_summary(
    mock_session,
) -> None:
    service = AssetService(mock_session)

    service.asset_repository.summary = AsyncMock(
        return_value={
            AssetStatus.IN_STOCK: 5,
            AssetStatus.ASSIGNED: 3,
            AssetStatus.REPAIR: 2,
            AssetStatus.RETIRED: 1,
        },
    )

    result = await service.summary()

    service.asset_repository.summary.assert_awaited_once()

    assert result == {
        "total": 11,
        "in_stock": 5,
        "assigned": 3,
        "repair": 2,
        "retired": 1,
    }
