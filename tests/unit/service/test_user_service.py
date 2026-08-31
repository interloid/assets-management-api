from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.auth import EmailAlreadyRegisteredError
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_register_creates_user_successfully(
    mock_session,
    user_payload,
) -> None:
    service = AuthService(mock_session)

    service.user_repository.get_by_email = AsyncMock(return_value=None)

    created_user = User(
        email=user_payload["email"],
        password_hash="hashed-password",
        full_name=user_payload["full_name"],
    )

    service.user_repository.create = AsyncMock(return_value=created_user)

    with patch(
        "app.services.auth.hash_password",
        return_value="hashed-password",
    ):
        result = await service.register(RegisterRequest(**user_payload))

    assert result is created_user
    assert result.email == user_payload["email"]
    assert result.full_name == user_payload["full_name"]

    service.user_repository.get_by_email.assert_awaited_once_with(user_payload["email"])

    service.user_repository.create.assert_awaited_once_with(
        email=user_payload["email"],
        password_hash="hashed-password",
        full_name=user_payload["full_name"],
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_hashes_password(
    mock_session,
    user_payload,
) -> None:
    service = AuthService(mock_session)

    service.user_repository.get_by_email = AsyncMock(return_value=None)

    created_user = User(
        email=user_payload["email"],
        password_hash="hashed-password",
        full_name=user_payload["full_name"],
    )

    service.user_repository.create = AsyncMock(return_value=created_user)

    with patch(
        "app.services.auth.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        await service.register(RegisterRequest(**user_payload))

    mock_hash_password.assert_called_once_with(user_payload["password"])

    service.user_repository.create.assert_awaited_once_with(
        email=user_payload["email"],
        password_hash="hashed-password",
        full_name=user_payload["full_name"],
    )


@pytest.mark.asyncio
async def test_register_raises_error_when_email_already_exists(
    mock_session,
    user_payload,
) -> None:
    service = AuthService(mock_session)

    existing_user = User(
        email=user_payload["email"],
        password_hash="existing-hash",
        full_name="Existing User",
    )

    service.user_repository.get_by_email = AsyncMock(return_value=existing_user)

    service.user_repository.create = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(RegisterRequest(**user_payload))

    service.user_repository.get_by_email.assert_awaited_once_with(user_payload["email"])

    service.user_repository.create.assert_not_awaited()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_rolls_back_when_create_raises_integrity_error(
    mock_session,
    user_payload,
) -> None:
    service = AuthService(mock_session)

    service.user_repository.get_by_email = AsyncMock(return_value=None)

    service.user_repository.create = AsyncMock(
        side_effect=IntegrityError(
            "duplicate",
            {},
            Exception("duplicate"),
        )
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(RegisterRequest(**user_payload))

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
