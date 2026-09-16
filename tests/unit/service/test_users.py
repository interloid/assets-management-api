from unittest.mock import AsyncMock

import pytest

from app.services.users import UserService


@pytest.mark.asyncio
async def test_list_users(
    mock_session,
    created_user,
) -> None:
    user_service = UserService(mock_session)

    user_service.user_repository.list_users = AsyncMock(
        return_value=([created_user], 1),
    )

    users, total = await user_service.list_users(
        page=1,
        size=20,
    )

    user_service.user_repository.list_users.assert_awaited_once_with(
        page=1,
        size=20,
        search=None,
    )

    assert users == [created_user]
    assert total == 1


@pytest.mark.asyncio
async def test_list_users_with_search(
    mock_session,
    created_user,
) -> None:
    user_service = UserService(mock_session)

    user_service.user_repository.list_users = AsyncMock(
        return_value=([created_user], 1),
    )

    users, total = await user_service.list_users(
        page=1,
        size=20,
        search="test@example.com",
    )

    user_service.user_repository.list_users.assert_awaited_once_with(
        page=1,
        size=20,
        search="test@example.com",
    )

    assert users == [created_user]
    assert total == 1


@pytest.mark.asyncio
async def test_list_users_empty_result(
    mock_session,
) -> None:
    user_service = UserService(mock_session)

    user_service.user_repository.list_users = AsyncMock(
        return_value=([], 0),
    )

    users, total = await user_service.list_users(
        page=2,
        size=20,
        search="does-not-exist",
    )

    user_service.user_repository.list_users.assert_awaited_once_with(
        page=2,
        size=20,
        search="does-not-exist",
    )

    assert users == []
    assert total == 0
