from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.auth import EmailAlreadyRegisteredError, InvalidTokenError


@pytest.mark.asyncio
async def test_valid_registration(
    auth_service,
    mock_session,
    user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)
    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    with patch(
        "app.services.auth.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        result = await auth_service.register(user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(user_payload.email),
    )

    mock_hash_password.assert_called_once_with(
        user_payload.password,
    )

    auth_service.user_repository.create.assert_awaited_once_with(
        email=str(user_payload.email),
        password_hash="hashed-password",
        full_name=user_payload.full_name,
    )

    mock_session.commit.assert_awaited_once()

    assert result is created_user


@pytest.mark.asyncio
async def test_duplicate_email(
    auth_service,
    mock_session,
    user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=created_user,
    )

    auth_service.user_repository.create = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(user_payload.email),
    )

    auth_service.user_repository.create.assert_not_awaited()
    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_hashed(
    auth_service,
    mock_session,
    user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=None,
    )

    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    with patch(
        "app.services.auth.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        await auth_service.register(user_payload)

    mock_hash_password.assert_called_once_with(
        user_payload.password,
    )

    auth_service.user_repository.create.assert_awaited_once_with(
        email=str(user_payload.email),
        password_hash="hashed-password",
        full_name=user_payload.full_name,
    )

    create_kwargs = auth_service.user_repository.create.await_args.kwargs

    assert create_kwargs["password_hash"] == "hashed-password"
    assert create_kwargs["password_hash"] != user_payload.password

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_integrity_error_handled(
    auth_service,
    mock_session,
    user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=None,
    )

    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    integrity_error = IntegrityError(
        "INSERT INTO users",
        {},
        Exception("duplicate key"),
    )

    mock_session.commit.side_effect = integrity_error

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(user_payload.email),
    )

    auth_service.user_repository.create.assert_awaited_once()

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_refresh_token(
    auth_service,
    refresh_token_repository,
    mock_session,
):
    with pytest.raises(InvalidTokenError):
        await auth_service.refresh("")

    refresh_token_repository.get_by_hash.assert_not_awaited()
    refresh_token_repository.revoke.assert_not_awaited()
    refresh_token_repository.revoke_family.assert_not_awaited()
    refresh_token_repository.create.assert_not_awaited()

    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()



