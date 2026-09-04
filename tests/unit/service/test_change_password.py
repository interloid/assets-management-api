from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import (
    InvalidCredentialsError,
    SamePasswordError,
)


@pytest.mark.asyncio
async def test_correct_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"
    redis_client = AsyncMock()

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        side_effect=[True, False],
    ) as mock_verify_password:
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            with patch(
                "app.services.auth.set_token_version",
                new_callable=AsyncMock,
            ) as mock_set_token_version:
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                    redis_client,
                )

    assert mock_verify_password.call_count == 2

    mock_verify_password.assert_any_call(
        current_password,
        created_user.password_hash,
    )

    mock_verify_password.assert_any_call(
        new_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_called_once_with(
        new_password,
    )

    auth_service.user_repository.update_password.assert_awaited_once_with(
        created_user,
        "new-hashed-password",
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        created_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        created_user,
    )

    mock_session.commit.assert_awaited_once()

    mock_set_token_version.assert_awaited_once_with(
        redis_client,
        str(created_user.id),
        created_user.token_version,
    )


@pytest.mark.asyncio
async def test_incorrect_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "WrongPassword123"
    new_password = "NewPassword123"
    redis_client = AsyncMock()

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        return_value=False,
    ) as mock_verify_password:
        with patch(
            "app.services.auth.hash_password",
        ) as mock_hash_password:
            with patch(
                "app.services.auth.set_token_version",
                new_callable=AsyncMock,
            ) as mock_set_token_version:
                with pytest.raises(InvalidCredentialsError):
                    await auth_service.change_password(
                        created_user,
                        current_password,
                        new_password,
                        redis_client,
                    )

    mock_verify_password.assert_called_once_with(
        current_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_not_called()

    auth_service.user_repository.update_password.assert_not_awaited()

    auth_service.refresh_token_repository.revoke_user.assert_not_awaited()

    auth_service.user_repository.increment_token_version.assert_not_awaited()

    mock_session.commit.assert_not_awaited()

    mock_session.rollback.assert_not_awaited()

    mock_set_token_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_password_rejected(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "OldPassword123"
    redis_client = AsyncMock()

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        side_effect=[True, True],
    ) as mock_verify_password:
        with patch(
            "app.services.auth.hash_password",
        ) as mock_hash_password:
            with patch(
                "app.services.auth.set_token_version",
                new_callable=AsyncMock,
            ) as mock_set_token_version:
                with pytest.raises(SamePasswordError):
                    await auth_service.change_password(
                        created_user,
                        current_password,
                        new_password,
                        redis_client,
                    )

    assert mock_verify_password.call_count == 2

    mock_verify_password.assert_any_call(
        current_password,
        created_user.password_hash,
    )

    mock_verify_password.assert_any_call(
        new_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_not_called()

    auth_service.user_repository.update_password.assert_not_awaited()

    auth_service.refresh_token_repository.revoke_user.assert_not_awaited()

    auth_service.user_repository.increment_token_version.assert_not_awaited()

    mock_session.commit.assert_not_awaited()

    mock_set_token_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_password_hashed(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"
    redis_client = AsyncMock()

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        side_effect=[True, False],
    ):
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            with patch(
                "app.services.auth.set_token_version",
                new_callable=AsyncMock,
            ):
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                    redis_client,
                )

    mock_hash_password.assert_called_once_with(
        new_password,
    )

    auth_service.user_repository.update_password.assert_awaited_once_with(
        created_user,
        "new-hashed-password",
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_all_refresh_tokens(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"
    redis_client = AsyncMock()

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        side_effect=[True, False],
    ):
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ):
            with patch(
                "app.services.auth.set_token_version",
                new_callable=AsyncMock,
            ):
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                    redis_client,
                )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        created_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        created_user,
    )

    mock_session.commit.assert_awaited_once()
