from datetime import datetime, timezone

import pytest
from uuid6 import uuid7

from app.api.v1.schemas.auth import LoginRequest, RegisterRequest
from app.modules.user.models import User
from app.shared.models.enums import UserRole


@pytest.fixture
def user() -> User:
    now = datetime.now(timezone.utc)

    return User(
        id=uuid7(),
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def register_user_payload() -> RegisterRequest:
    return RegisterRequest(
        email="test@example.com",
        password="Password123",
        full_name="Test User",
    )


@pytest.fixture
def login_payload() -> LoginRequest:
    return LoginRequest(
        email="test@example.com",
        password="Password123",
    )


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {
        "email": "test@example.com",
        "password": "Password123",
        "full_name": "Test User",
    }
