from unittest.mock import AsyncMock, patch

import pytest
from uuid6 import uuid7

from app.dependencies.authentication import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_success(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()
    token = "valid access token"

    created_user.id = uuid7()
    created_user.token_version = 0

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    mock_repository = AsyncMock()
    mock_repository.get_by_id.return_value = created_user

    with (
        patch(
            "app.dependencies.authentication.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 0,
            },
        ),
        patch(
            "app.dependencies.authentication.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_blacklist,
        patch(
            "app.dependencies.authentication.get_token_version",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_get_token_version,
        patch(
            "app.dependencies.authentication.UserRepository",
            return_value=mock_repository,
        ),
    ):
        result = await get_current_user(
            credentials=mock_credentials,
            session=mock_session,
            redis_client=mock_redis,
        )

    assert result is created_user

    mock_blacklist.assert_awaited_once_with(
        mock_redis,
        "jti-123",
    )

    mock_get_token_version.assert_awaited_once_with(
        mock_redis,
        str(created_user.id),
    )

    mock_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )


@pytest.mark.asyncio
async def test_get_current_user_redis_miss(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()
    token = "valid access token"

    created_user.id = uuid7()
    created_user.token_version = 3

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    mock_repository = AsyncMock()
    mock_repository.get_by_id.return_value = created_user

    with (
        patch(
            "app.dependencies.authentication.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 3,
            },
        ),
        patch(
            "app.dependencies.authentication.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.dependencies.authentication.get_token_version",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_get_token_version,
        patch(
            "app.dependencies.authentication.set_token_version",
            new_callable=AsyncMock,
        ) as mock_set_token_version,
        patch(
            "app.dependencies.authentication.UserRepository",
            return_value=mock_repository,
        ),
    ):
        result = await get_current_user(
            credentials=mock_credentials,
            session=mock_session,
            redis_client=mock_redis,
        )

    assert result is created_user

    mock_get_token_version.assert_awaited_once_with(
        mock_redis,
        str(created_user.id),
    )

    mock_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )

    mock_set_token_version.assert_awaited_once_with(
        mock_redis,
        str(created_user.id),
        3,
    )


@pytest.mark.asyncio
async def test_get_current_user_token_version_mismatch(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()

    created_user.id = uuid7()
    created_user.token_version = 2

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": "valid access token"},
    )()

    mock_repository = AsyncMock()

    with (
        patch(
            "app.dependencies.authentication.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 1,
            },
        ),
        patch(
            "app.dependencies.authentication.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.dependencies.authentication.get_token_version",
            new_callable=AsyncMock,
            return_value=2,
        ),
        patch(
            "app.dependencies.authentication.UserRepository",
            return_value=mock_repository,
        ),
    ):
        from app.exceptions.auth import InvalidTokenError

        with pytest.raises(InvalidTokenError):
            await get_current_user(
                credentials=mock_credentials,
                session=mock_session,
                redis_client=mock_redis,
            )

    mock_repository.get_by_id.assert_not_awaited()
