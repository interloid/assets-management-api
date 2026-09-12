from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from uuid6 import uuid7

from app.models.refresh_token import RefreshToken
from app.services.auth import AuthService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def refresh_token_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def auth_service(
    mock_session: AsyncMock,
    user_repository: AsyncMock,
    refresh_token_repository: AsyncMock,
) -> AuthService:
    service = AuthService(session=mock_session)

    service.user_repository = user_repository
    service.refresh_token_repository = refresh_token_repository

    return service


# @pytest.fixture
# def login_payload() -> LoginRequest:
#     return LoginRequest(
#         email="test@example.com",
#         password="Password123",
#     )


@pytest.fixture
def active_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="user-123",
        password_hash="hashed-password",
        role=SimpleNamespace(value="user"),
        is_active=True,
        token_version=0,
    )


@pytest.fixture
def inactive_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="user-123",
        password_hash="hashed-password",
        role=SimpleNamespace(value="user"),
        is_active=False,
    )


@pytest.fixture
def refresh_token() -> str:
    return "old-refresh-token"


@pytest.fixture
def valid_stored_token() -> SimpleNamespace:
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=None,
    )


@pytest.fixture
def expired_stored_token() -> SimpleNamespace:
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        revoked_at=None,
    )


@pytest.fixture
def revoked_stored_token() -> SimpleNamespace:
    return SimpleNamespace(
        id="token-123",
        user_id="user-123",
        family_id="family-123",
        token_hash="old-token-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def created_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="user-123",
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=SimpleNamespace(value="user"),
        is_active=True,
        token_version=0,
    )


@pytest.fixture
def created_refresh_token() -> RefreshToken:
    return RefreshToken(
        id=uuid7(),
        user_id=uuid7(),
        token_hash="hashed_refresh_token",
        family_id=uuid7(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=None,
    )
