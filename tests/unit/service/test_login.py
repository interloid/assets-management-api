from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidCredentialsError


@pytest.mark.asyncio
async def test_valid_credentials(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:
    """AUTH-LOGIN-01: Valid credentials return access and refresh tokens."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=active_user)

    auth_service.refresh_token_repository.create = AsyncMock()

    with (
        patch(
            "app.services.auth.verify_password",
            return_value=True,
        ) as mock_verify_password,
        patch(
            "app.services.auth.create_access_token",
            return_value="access-token",
        ) as mock_create_access_token,
        patch(
            "app.services.auth.generate_refresh_token",
            return_value="refresh-token",
        ) as mock_generate_refresh_token,
        patch(
            "app.services.auth.hash_refresh_token",
            return_value="refresh-token-hash",
        ) as mock_hash_refresh_token,
    ):
        result = await auth_service.login(login_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        login_payload.email
    )

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        active_user.password_hash,
    )

    mock_create_access_token.assert_called_once_with(
        user_id=str(active_user.id),
        role=active_user.role.value,
    )

    mock_generate_refresh_token.assert_called_once()

    mock_hash_refresh_token.assert_called_once_with("refresh-token")

    auth_service.refresh_token_repository.create.assert_awaited_once()

    mock_session.commit.assert_awaited_once()

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"


@pytest.mark.asyncio
async def test_unknown_email(
    auth_service,
    mock_session,
    login_payload,
) -> None:
    """AUTH-LOGIN-02: Unknown email is rejected."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)

    with (
        patch("app.services.auth.verify_password") as mock_verify_password,
        patch("app.services.auth.create_access_token") as mock_create_access_token,
        patch(
            "app.services.auth.generate_refresh_token"
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        login_payload.email
    )

    mock_verify_password.assert_not_called()
    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_incorrect_password(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:
    """AUTH-LOGIN-03: Incorrect password is rejected."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=active_user)

    with (
        patch(
            "app.services.auth.verify_password",
            return_value=False,
        ) as mock_verify_password,
        patch("app.services.auth.create_access_token") as mock_create_access_token,
        patch(
            "app.services.auth.generate_refresh_token"
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login_payload)

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        active_user.password_hash,
    )

    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_user(
    auth_service,
    mock_session,
    login_payload,
    inactive_user,
) -> None:
    """AUTH-LOGIN-04: Inactive user is rejected."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=inactive_user)

    with (
        patch(
            "app.services.auth.verify_password",
            return_value=True,
        ) as mock_verify_password,
        patch("app.services.auth.create_access_token") as mock_create_access_token,
        patch(
            "app.services.auth.generate_refresh_token"
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login_payload)

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        inactive_user.password_hash,
    )

    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_token_created(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:
    """AUTH-LOGIN-05: Refresh token is generated, hashed, and persisted."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=active_user)

    auth_service.refresh_token_repository.create = AsyncMock()

    with (
        patch(
            "app.services.auth.verify_password",
            return_value=True,
        ),
        patch(
            "app.services.auth.create_access_token",
            return_value="access-token",
        ),
        patch(
            "app.services.auth.generate_refresh_token",
            return_value="refresh-token",
        ) as mock_generate_refresh_token,
        patch(
            "app.services.auth.hash_refresh_token",
            return_value="hashed-refresh-token",
        ) as mock_hash_refresh_token,
    ):
        result = await auth_service.login(login_payload)

    mock_generate_refresh_token.assert_called_once()

    mock_hash_refresh_token.assert_called_once_with("refresh-token")

    auth_service.refresh_token_repository.create.assert_awaited_once()

    create_kwargs = auth_service.refresh_token_repository.create.await_args.kwargs

    assert create_kwargs["user_id"] == active_user.id
    assert create_kwargs["token_hash"] == "hashed-refresh-token"
    assert create_kwargs["family_id"] is not None
    assert create_kwargs["expires_at"] is not None

    mock_session.commit.assert_awaited_once()

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
