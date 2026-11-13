from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.asset.exceptions import (
    AssetAssignmentUserNotFoundError,
    AssetNotFoundError,
)
from app.modules.asset.services import AssetService
from app.modules.auth.exceptions import (
    AuthorizationError,
)
from app.shared.models.enums import UserRole


@pytest.fixture
def service():
    redis_client = MagicMock()
    session = MagicMock()
    instance = AssetService(session, redis_client)

    instance.asset_repository = MagicMock()
    instance.user_repository = MagicMock()

    instance.asset_repository.get_by_id = AsyncMock()
    instance.asset_repository.get_history_by_asset_id = AsyncMock()
    instance.asset_repository.get_history_by_user_id = AsyncMock()
    instance.user_repository.get_by_id = AsyncMock()

    return instance


@pytest.mark.asyncio
async def test_get_history_by_asset_returns_asset_id_and_history(service):
    asset_id = uuid4()
    asset = MagicMock()
    history = [MagicMock(), MagicMock()]
    total = 10

    service.asset_repository.get_by_id.return_value = asset
    service.asset_repository.get_history_by_asset_id.return_value = (
        history,
        total,
    )

    returned_id, returned_history, returned_total = await service.get_history_by_asset(
        asset_id=asset_id,
        page=1,
        size=5,
        search="john",
    )

    assert returned_id == asset_id
    assert returned_history == history
    assert returned_total == total

    service.asset_repository.get_by_id.assert_awaited_once_with(asset_id)
    service.asset_repository.get_history_by_asset_id.assert_awaited_once_with(
        asset_id=asset_id,
        page=1,
        size=5,
        search="john",
    )


@pytest.mark.asyncio
async def test_get_history_by_asset_raises_when_asset_missing(service):
    asset_id = uuid4()
    service.asset_repository.get_by_id.return_value = None

    with pytest.raises(AssetNotFoundError):
        await service.get_history_by_asset(asset_id=asset_id, page=1, size=5)

    service.asset_repository.get_history_by_asset_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_history_by_asset_returns_empty_history(service):
    asset_id = uuid4()
    service.asset_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_asset_id.return_value = ([], 0)

    returned_id, history, total = await service.get_history_by_asset(
        asset_id=asset_id,
        page=1,
        size=5,
        search=None,
    )

    assert returned_id == asset_id
    assert history == []
    assert total == 0

    service.asset_repository.get_by_id.assert_awaited_once_with(asset_id)
    service.asset_repository.get_history_by_asset_id.assert_awaited_once_with(
        asset_id=asset_id,
        page=1,
        size=5,
        search=None,
    )


@pytest.mark.asyncio
async def test_admin_can_get_any_users_history(service):
    user_id = uuid4()
    admin = MagicMock()
    admin.role = UserRole.ADMIN
    admin.id = uuid4()

    user = MagicMock()
    history = [MagicMock()]
    total = 10

    service.user_repository.get_by_id.return_value = user
    service.asset_repository.get_history_by_user_id.return_value = (
        history,
        total,
    )

    result, result_total = await service.get_history_by_user(
        user_id=user_id,
        current_user=admin,
        page=2,
        size=5,
        search="IL-LAP",
    )

    assert result == history
    assert result_total == total

    service.user_repository.get_by_id.assert_awaited_once_with(
        user_id=user_id,
    )
    service.asset_repository.get_history_by_user_id.assert_awaited_once_with(
        user_id=user_id,
        page=2,
        size=5,
        search="IL-LAP",
    )


@pytest.mark.asyncio
async def test_user_can_get_own_history(service):
    user_id = uuid4()
    current_user = MagicMock()
    current_user.id = user_id
    current_user.role = UserRole.USER

    history = [MagicMock()]

    service.user_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_user_id.return_value = (
        history,
        1,
    )

    result, total = await service.get_history_by_user(
        user_id=user_id,
        current_user=current_user,
        page=1,
        size=5,
    )

    assert result == history
    assert total == 1

    service.asset_repository.get_history_by_user_id.assert_awaited_once_with(
        user_id=user_id,
        page=1,
        size=5,
        search=None,
    )


@pytest.mark.asyncio
async def test_user_cannot_get_another_users_history(service):
    requested_user_id = uuid4()
    current_user = MagicMock()
    current_user.id = uuid4()
    current_user.role = UserRole.USER

    service.user_repository.get_by_id.return_value = MagicMock()

    with pytest.raises(AuthorizationError):
        await service.get_history_by_user(
            user_id=requested_user_id,
            current_user=current_user,
            page=1,
            size=5,
        )

    service.asset_repository.get_history_by_user_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_history_by_user_raises_when_user_missing(service):
    user_id = uuid4()
    current_user = MagicMock()
    current_user.id = user_id
    current_user.role = UserRole.USER

    service.user_repository.get_by_id.return_value = None

    with pytest.raises(AssetAssignmentUserNotFoundError):
        await service.get_history_by_user(
            user_id=user_id,
            current_user=current_user,
            page=1,
            size=5,
        )

    service.asset_repository.get_history_by_user_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_history_by_user_returns_empty_history(service):
    user_id = uuid4()
    current_user = MagicMock()
    current_user.id = user_id
    current_user.role = UserRole.USER

    service.user_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_user_id.return_value = ([], 0)

    result, total = await service.get_history_by_user(
        user_id=user_id,
        current_user=current_user,
        page=1,
        size=5,
    )

    assert result == []
    assert total == 0
