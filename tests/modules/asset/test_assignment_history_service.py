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

    service.asset_repository.get_by_id.return_value = asset
    service.asset_repository.get_history_by_asset_id.return_value = history

    returned_id, returned_history = await service.get_history_by_asset(
        asset_id,
    )

    assert returned_id == asset_id
    assert returned_history == history
    service.asset_repository.get_by_id.assert_awaited_once_with(asset_id)
    service.asset_repository.get_history_by_asset_id.assert_awaited_once_with(
        asset_id,
    )


@pytest.mark.asyncio
async def test_get_history_by_asset_raises_when_asset_missing(service):
    asset_id = uuid4()
    service.asset_repository.get_by_id.return_value = None

    with pytest.raises(AssetNotFoundError):
        await service.get_history_by_asset(asset_id)

    service.asset_repository.get_history_by_asset_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_history_by_asset_returns_empty_history(service):
    asset_id = uuid4()
    service.asset_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_asset_id.return_value = []

    returned_id, history = await service.get_history_by_asset(asset_id)

    assert returned_id == asset_id
    assert history == []


@pytest.mark.asyncio
async def test_admin_can_get_any_users_history(service):
    user_id = uuid4()
    admin = MagicMock()
    admin.role = UserRole.ADMIN
    admin.id = uuid4()

    user = MagicMock()
    history = [MagicMock()]

    service.user_repository.get_by_id.return_value = user
    service.asset_repository.get_history_by_user_id.return_value = history

    result = await service.get_history_by_user(
        user_id=user_id,
        current_user=admin,
    )

    assert result == history
    service.user_repository.get_by_id.assert_awaited_once_with(
        user_id=user_id,
    )
    service.asset_repository.get_history_by_user_id.assert_awaited_once_with(
        user_id=user_id,
    )


@pytest.mark.asyncio
async def test_user_can_get_own_history(service):
    user_id = uuid4()
    current_user = MagicMock()
    current_user.id = user_id
    current_user.role = UserRole.USER

    history = [MagicMock()]
    service.user_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_user_id.return_value = history

    result = await service.get_history_by_user(
        user_id=user_id,
        current_user=current_user,
    )

    assert result == history


@pytest.mark.asyncio
async def test_user_cannot_get_another_users_history(service):
    requested_user_id = uuid4()
    current_user = MagicMock()
    current_user.id = uuid4()
    current_user.role = UserRole.USER

    service.user_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_user_id.return_value = [
        MagicMock(),
    ]

    with pytest.raises(AuthorizationError):
        await service.get_history_by_user(
            user_id=requested_user_id,
            current_user=current_user,
        )


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
        )

    service.asset_repository.get_history_by_user_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_history_by_user_returns_empty_history(service):
    user_id = uuid4()
    current_user = MagicMock()
    current_user.id = user_id
    current_user.role = UserRole.USER

    service.user_repository.get_by_id.return_value = MagicMock()
    service.asset_repository.get_history_by_user_id.return_value = []

    result = await service.get_history_by_user(
        user_id=user_id,
        current_user=current_user,
    )

    assert result == []
