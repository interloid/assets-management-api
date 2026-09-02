from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidTokenError


@pytest.mark.asyncio
async def test_valid_logout(auth_service, mock_session, created_refresh_token) -> None:
    refresh_token = "valid refresh token"

    with patch(
        "app.services.auth.hash_refresh_token",
        return_value="hashed_refresh_token",
    ) as mock_hash:
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=created_refresh_token,
        )

        auth_service.refresh_token_repository.revoke = AsyncMock()

        await auth_service.logout(refresh_token)

        mock_hash.assert_called_once_with(refresh_token)

        auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
            "hashed_refresh_token",
            for_update=True,
        )

        auth_service.refresh_token_repository.revoke.assert_awaited_once_with(
            created_refresh_token.id
        )

        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_empty_refresh_token(
    auth_service,
) -> None:
    with pytest.raises(InvalidTokenError):
        await auth_service.logout("")

    auth_service.refresh_token_repository.get_by_hash.assert_not_awaited()


@pytest.mark.asyncio
async def test_logout_refresh_token_not_found(
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
            await auth_service.logout(refresh_token)

        auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
            "hashed_refresh_token",
            for_update=True,
        )

        auth_service.refresh_token_repository.revoke.assert_not_awaited()

        mock_session.commit.assert_not_awaited()
