from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.dependencies.authentication import get_current_user
from app.dependencies.redis import get_redis
from app.exceptions.auth import InvalidTokenError
from app.main import app


@pytest.mark.asyncio
async def test_logout_all_success(
    api_client,
) -> None:
    refresh_token = "valid_refresh_token"
    mock_redis = AsyncMock()

    current_user = SimpleNamespace(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=SimpleNamespace(value="user"),
        is_active=True,
        token_version=0,
    )

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_redis] = lambda: mock_redis

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    try:
        with patch(
            "app.routers.auth.AuthService.logout_all",
            new_callable=AsyncMock,
        ) as mock_logout_all:
            response = await api_client.post("/auth/logout-all")

        assert response.status_code == 204

        mock_logout_all.assert_awaited_once_with(
            refresh_token,
            current_user,
            mock_redis,
        )

        assert "refresh_token" in response.headers.get(
            "set-cookie",
            "",
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logout_all_failed(
    api_client,
) -> None:
    refresh_token = "invalid_refresh_token"
    mock_redis = AsyncMock()

    current_user = SimpleNamespace(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        role=SimpleNamespace(value="user"),
        is_active=True,
        token_version=0,
    )

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_redis] = lambda: mock_redis

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    try:
        with patch(
            "app.routers.auth.AuthService.logout_all",
            new_callable=AsyncMock,
            side_effect=InvalidTokenError(),
        ) as mock_logout_all:
            response = await api_client.post("/auth/logout-all")

        assert response.status_code == 401

        mock_logout_all.assert_awaited_once_with(
            refresh_token,
            current_user,
            mock_redis,
        )
    finally:
        app.dependency_overrides.clear()
