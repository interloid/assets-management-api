from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth import AuthService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def refresh_token_repository():
    return AsyncMock()


@pytest.fixture
def auth_service(
    mock_session,
    user_repository,
    refresh_token_repository,
):
    service = AuthService(session=mock_session)

    service.user_repository = user_repository
    service.refresh_token_repository = refresh_token_repository

    return service


@pytest.fixture
def user_payload() -> RegisterRequest:
    return RegisterRequest(
        email="test@example.com",
        password="Password123",
        full_name="Test User",
    )


@pytest.fixture
def login_payload() -> LoginRequest:
    return LoginRequest(
        email="user@example.com",
        password="Password123",
    )


@pytest.fixture
def active_user():
    return SimpleNamespace(
        id="user-123",
        password_hash="hashed-password",
        role=SimpleNamespace(value="user"),
        is_active=True,
    )


@pytest.fixture
def inactive_user():
    return SimpleNamespace(
        id="user-123",
        password_hash="hashed-password",
        role=SimpleNamespace(value="user"),
        is_active=False,
    )


@pytest.fixture
def refresh_token():
    return "old-refresh-token"


@pytest.fixture
def valid_stored_token():
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=None,
    )


@pytest.fixture
def expired_stored_token():
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        revoked_at=None,
    )


@pytest.fixture
def revoked_stored_token():
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def created_user():
    return SimpleNamespace(
        id="user-123",
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=SimpleNamespace(value="user"),
        is_active=True,
    )
