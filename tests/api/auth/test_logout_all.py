from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_logout_all_success(
    api_client,
) -> None:
    refresh_token = "valid_refresh_token"

    api_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    with patch(
        "app.routers.auth.AuthService.logout_all",
        new_callable=AsyncMock,
    ) as mock_logout_all:
        response = await api_client.post("/auth/logout-all")

    assert response.status_code == 204
    assert response.content == b""

    mock_logout_all.assert_awaited_once_with(
        refresh_token,
    )
