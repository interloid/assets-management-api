from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidTokenError


@pytest.mark.asyncio
async def test_logout_success(api_client) -> None:
    refresh_token = "valid_refresh_token"

    api_client.cookies.set("refresh_token", refresh_token)

    with patch(
        "app.routers.auth.AuthService.logout",
        new_callable=AsyncMock,
    ) as mock_logout:
        response = await api_client.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""

    mock_logout.assert_awaited_once_with(
        refresh_token,
    )


@pytest.mark.asyncio
async def test_logout_failed(
    api_client,
) -> None:
    refresh_token = "invalid_refresh_token"

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    with patch(
        "app.routers.auth.AuthService.logout",
        new_callable=AsyncMock,
        side_effect=InvalidTokenError(),
    ) as mock_logout:
        response = await api_client.post("/auth/logout")

    assert response.status_code == 401

    mock_logout.assert_awaited_once_with(
        refresh_token,
    )

    body = response.json()

    assert body["detail"] == "Invalid or expired token"
