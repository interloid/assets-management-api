from unittest.mock import AsyncMock

import pytest

from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth import AuthService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def auth_service(mock_session: AsyncMock) -> AuthService:
    return AuthService(mock_session)


@pytest.fixture
def user_payload() -> RegisterRequest:
    return RegisterRequest(
        email="test@example.com",
        password="Password123",
        full_name="Test User",
    )

@pytest.fixture
def active_user() -> User:
    return User(
        email="user@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
    )


@pytest.fixture
def inactive_user() -> User:
    return User(
        email="inactive@example.com",
        password_hash="hashed-password",
        full_name="Inactive User",
        role=UserRole.USER,
        is_active=False,
    )


@pytest.fixture
def created_user(user_payload: RegisterRequest) -> User:
    return User(
        email=str(user_payload.email),
        password_hash="hashed-password",
        full_name=user_payload.full_name,
        role=UserRole.USER,
        is_active=True,
    )
