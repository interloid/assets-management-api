from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidCredentialsError


@pytest.mark.asyncio
async def test_correct_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        return_value=True,
    ) as mock_verify_password:
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
            )

    mock_verify_password.assert_called_once_with(
        current_password,
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

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_incorrect_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "WrongPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.get_by_id = AsyncMock(
        return_value=created_user,
    )

    auth_service.user_repository.update_password = AsyncMock()

    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        return_value=False,
    ) as mock_verify_password:
        with patch(
            "app.services.auth.hash_password",
        ) as mock_hash_password:
            with pytest.raises(InvalidCredentialsError):
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                )

    mock_verify_password.assert_called_once_with(
        current_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_not_called()

    auth_service.user_repository.update_password.assert_not_awaited()

    auth_service.refresh_token_repository.revoke_all_for_user.assert_not_awaited()

    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_password_hashed(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.get_by_id = AsyncMock(
        return_value=created_user,
    )

    auth_service.user_repository.update_password = AsyncMock()

    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        return_value=True,
    ):
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
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

    auth_service.user_repository.get_by_id = AsyncMock(
        return_value=created_user,
    )

    auth_service.user_repository.update_password = AsyncMock()

    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    with patch(
        "app.services.auth.verify_password",
        return_value=True,
    ):
        with patch(
            "app.services.auth.hash_password",
            return_value="new-hashed-password",
        ):
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
            )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        created_user.id,
    )

    mock_session.commit.assert_awaited_once()

