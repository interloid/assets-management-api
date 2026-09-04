from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidTokenError


@pytest.mark.asyncio
async def test_logout_all_success(
    auth_service,
    mock_session,
    valid_stored_token,
) -> None:
    refresh_token = "valid_refresh_token"
    redis_client = AsyncMock()

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    with patch(
        "app.services.auth.hash_refresh_token",
        return_value="hashed_refresh_token",
    ) as mock_hash:
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=valid_stored_token,
        )

        auth_service.refresh_token_repository.revoke_all_for_user = AsyncMock()

        auth_service.user_repository.increment_token_version = AsyncMock(
            side_effect=lambda user: setattr(
                user,
                "token_version",
                user.token_version + 1,
            ),
        )

        with patch(
            "app.services.auth.set_token_version",
            new_callable=AsyncMock,
        ) as mock_set_token_version:
            await auth_service.logout_all(
                refresh_token,
                current_user,
                redis_client,
            )

    mock_hash.assert_called_once_with(refresh_token)

    auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "hashed_refresh_token",
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        current_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        current_user,
    )

    mock_session.commit.assert_awaited_once()

    assert current_user.token_version == 1

    mock_set_token_version.assert_awaited_once_with(
        redis_client,
        str(current_user.id),
        1,
    )

@pytest.mark.asyncio
async def test_logout_all_empty_refresh_token(
    auth_service,
) -> None:
    refresh_token = ""
    redis_client = AsyncMock()

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    with pytest.raises(InvalidTokenError):
        await auth_service.logout_all(
            refresh_token,
            current_user,
            redis_client,
        )

@pytest.mark.asyncio
async def test_logout_all_refresh_token_not_found(
    auth_service,
    mock_session,
) -> None:
    refresh_token = "invalid_refresh_token"
    redis_client = AsyncMock()

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    with patch(
        "app.services.auth.hash_refresh_token",
        return_value="hashed_refresh_token",
    ):
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=None,
        )

        with pytest.raises(InvalidTokenError):
            await auth_service.logout_all(
                refresh_token,
                current_user,
                redis_client,
            )
