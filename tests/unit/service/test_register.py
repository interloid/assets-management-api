from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.auth import EmailAlreadyRegisteredError


@pytest.mark.asyncio
async def test_valid_registration(
    auth_service,
    mock_session,
    user_payload,
    created_user,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)

    auth_service.user_repository.create = AsyncMock(return_value=created_user)

    with patch(
        "app.services.auth.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        result = await auth_service.register(user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(user_payload.email)
    )

    mock_hash_password.assert_called_once_with(user_payload.password)

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

    auth_service.user_repository.get_by_email = AsyncMock(return_value=created_user)

    auth_service.user_repository.create = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(user_payload.email)
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
    """AUTH-REG-03: Plain password is hashed before persistence."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)

    auth_service.user_repository.create = AsyncMock(return_value=created_user)

    with patch(
        "app.services.auth.hash_password",
        return_value="bcrypt-hash",
    ) as mock_hash_password:
        await auth_service.register(user_payload)

    mock_hash_password.assert_called_once_with(user_payload.password)

    auth_service.user_repository.create.assert_awaited_once()

    create_kwargs = auth_service.user_repository.create.await_args.kwargs

    assert create_kwargs["password_hash"] == "bcrypt-hash"
    assert create_kwargs["password_hash"] != user_payload.password

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_integrity_error_handled(
    auth_service,
    mock_session,
    user_payload,
) -> None:
    """AUTH-REG-04: IntegrityError is rolled back and translated."""

    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)

    integrity_error = IntegrityError(
        "INSERT INTO users",
        {},
        Exception("duplicate key"),
    )

    auth_service.user_repository.create = AsyncMock(side_effect=integrity_error)

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(user_payload)

    auth_service.user_repository.create.assert_awaited_once()

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
