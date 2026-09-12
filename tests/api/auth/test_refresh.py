from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import (
    InvalidTokenError,
    RefreshTokenReuseError,
)
from app.schemas.auth import LoginResult


@pytest.mark.asyncio
async def test_valid_refresh(
    api_client,
) -> None:
    refresh_token = "valid-refresh-token"

    result = LoginResult(
        access_token="new-access-token",
        refresh_token="new-refresh-token",
    )

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    with patch(
        "app.routers.auth.AuthService.refresh",
        new_callable=AsyncMock,
        return_value=result,
    ) as mock_refresh:
        response = await api_client.post(
            "/auth/refresh",
        )

    assert response.status_code == 200

    mock_refresh.assert_awaited_once_with(
        refresh_token,
    )

    body = response.json()

    assert body["success"] is True
    assert body["statusCode"] == 200
    assert body["message"] == "Token refreshed successfully"
    assert body["data"]["access_token"] == "new-access-token"
    assert body["data"]["token_type"] == "bearer"
    assert body["error"] is None

    assert "refresh_token" not in body

    assert response.cookies["refresh_token"] == "new-refresh-token"


@pytest.mark.asyncio
async def test_invalid_token(
    api_client,
) -> None:
    refresh_token = "invalid-refresh-token"

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    with patch(
        "app.routers.auth.AuthService.refresh",
        new_callable=AsyncMock,
        side_effect=InvalidTokenError(),
    ) as mock_refresh:
        response = await api_client.post(
            "/auth/refresh",
        )

    assert response.status_code == 401

    mock_refresh.assert_awaited_once_with(
        refresh_token,
    )

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 401
    assert body["message"] == "Invalid or expired token"
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_TOKEN"
    assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_api_refresh_04_reuse_detection(
    api_client,
) -> None:
    refresh_token = "reused-refresh-token"

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    with patch(
        "app.routers.auth.AuthService.refresh",
        new_callable=AsyncMock,
        side_effect=RefreshTokenReuseError(),
    ) as mock_refresh:
        response = await api_client.post(
            "/auth/refresh",
        )

    assert response.status_code == 401

    mock_refresh.assert_awaited_once_with(
        refresh_token,
    )

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 401
    assert body["message"] == "Refresh token has already been used"
    assert body["data"] is None
    assert body["error"]["code"] == "REFRESH_TOKEN_REUSE"
    assert body["error"]["details"] is None
