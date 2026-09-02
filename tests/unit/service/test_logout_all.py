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

    with patch(
        "app.services.auth.hash_refresh_token",
        return_value="hashed_refresh_token",
    ) as mock_hash:
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=valid_stored_token,
        )

        auth_service.refresh_token_repository.revoke_user = AsyncMock()

        await auth_service.logout_all(refresh_token)

        mock_hash.assert_called_once_with(refresh_token)

        auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
            "hashed_refresh_token",
        )

        auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
            valid_stored_token.user_id,
        )

        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_all_empty_refresh_token(
    auth_service,
) -> None:
    with pytest.raises(InvalidTokenError):
        await auth_service.logout_all("")

    auth_service.refresh_token_repository.get_by_hash.assert_not_awaited()


@pytest.mark.asyncio
async def test_logout_all_refresh_token_not_found(
    auth_service,
    mock_session,
) -> None:
    refresh_token = "invalid_refresh_token"

    with patch(
        "app.services.auth.hash_refresh_token",
        return_value="hashed_refresh_token",
    ):
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=None,
        )

        with pytest.raises(InvalidTokenError):
            await auth_service.logout_all(refresh_token)

        auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
            "hashed_refresh_token",
        )

        auth_service.refresh_token_repository.revoke_user.assert_not_awaited()

        mock_session.commit.assert_not_awaited()
