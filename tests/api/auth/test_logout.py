from unittest.mock import AsyncMock, patch

import pytest

from app.dependencies.authentication import get_current_access_token
from app.exceptions.auth import InvalidTokenError
from app.main import app


@pytest.mark.asyncio
async def test_logout_success(api_client) -> None:
    refresh_token = "valid_refresh_token"

    access_token_payload = {
        "jti": "jti-123",
        "exp": 9999999999,
    }

    app.dependency_overrides[get_current_access_token] = lambda: access_token_payload

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    try:
        with patch(
            "app.routers.auth.AuthService.logout",
            new_callable=AsyncMock,
        ) as mock_logout:
            response = await api_client.post("/auth/logout")

        assert response.status_code == 204

        mock_logout.assert_awaited_once_with(
            refresh_token,
            access_token_payload,
            app.state.redis,
        )

        assert "refresh_token" in response.headers.get(
            "set-cookie",
            "",
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logout_failed(
    api_client,
) -> None:
    refresh_token = "invalid_refresh_token"

    access_token_payload = {
        "jti": "jti-123",
        "exp": 9999999999,
    }

    app.dependency_overrides[get_current_access_token] = lambda: access_token_payload

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    try:
        with patch(
            "app.routers.auth.AuthService.logout",
            new_callable=AsyncMock,
            side_effect=InvalidTokenError(),
        ) as mock_logout:
            response = await api_client.post("/auth/logout")

        assert response.status_code == 401

        mock_logout.assert_awaited_once_with(
            refresh_token,
            access_token_payload,
            app.state.redis,
        )
    finally:
        app.dependency_overrides.clear()
