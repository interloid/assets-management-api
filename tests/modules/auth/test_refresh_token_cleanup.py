from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.auth.services import AuthService


@pytest.mark.asyncio
async def test_cleanup_expired_refresh_tokens_success(
    mock_session,
) -> None:
    mock_repository = AsyncMock()
    mock_repository.delete_old_tokens.return_value = 5

    with patch(
        "app.modules.auth.services.RefreshTokenRepository",
        return_value=mock_repository,
    ):
        service = AuthService(mock_session)

        before_cleanup = datetime.now(timezone.utc)

        result = await service.cleanup_expired_refresh_tokens()

        after_cleanup = datetime.now(timezone.utc)

    assert result == {
        "deleted_refresh_tokens": 5,
    }

    mock_repository.delete_old_tokens.assert_awaited_once()

    cutoff = mock_repository.delete_old_tokens.await_args.args[0]

    expected_cutoff = timedelta(days=90)

    assert before_cleanup - expected_cutoff <= cutoff
    assert cutoff <= after_cleanup - expected_cutoff

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_no_expired_refresh_tokens(
    mock_session,
) -> None:
    mock_repository = AsyncMock()
    mock_repository.delete_old_tokens.return_value = 0

    with patch(
        "app.modules.auth.services.RefreshTokenRepository",
        return_value=mock_repository,
    ):
        service = AuthService(mock_session)

        result = await service.cleanup_expired_refresh_tokens()

    assert result == {
        "deleted_refresh_tokens": 0,
    }

    mock_repository.delete_old_tokens.assert_awaited_once()

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_rolls_back_on_failure(
    mock_session,
) -> None:
    mock_repository = AsyncMock()
    mock_repository.delete_old_tokens.side_effect = RuntimeError(
        "Database deletion failed",
    )

    with patch(
        "app.modules.auth.services.RefreshTokenRepository",
        return_value=mock_repository,
    ):
        service = AuthService(mock_session)

        with pytest.raises(
            RuntimeError,
            match="Database deletion failed",
        ):
            await service.cleanup_expired_refresh_tokens()

    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_awaited_once()
