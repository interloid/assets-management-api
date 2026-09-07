from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import InvalidCredentialsError
from app.schemas.auth import LoginResult


@pytest.mark.asyncio
async def test_login_success(
    api_client,
    login_payload,
) -> None:
    login_result = LoginResult(
        access_token="access-token",
        refresh_token="refresh-token",
    )

    with patch(
        "app.routers.auth.AuthService.login",
        new_callable=AsyncMock,
        return_value=login_result,
    ) as mock_login:
        response = await api_client.post(
            "/auth/login",
            json=login_payload.model_dump(),
        )

    assert response.status_code == 200

    mock_login.assert_awaited_once()

    body = response.json()

    assert body["success"] is True
    assert body["statusCode"] == 200
    assert body["message"] == "Login successful"
    assert body["data"]["access_token"] == "access-token"
    assert body["data"]["token_type"] == "bearer"
    assert body["error"] is None

    assert "refresh_token" not in body
    assert response.cookies["refresh_token"] == "refresh-token"


@pytest.mark.asyncio
async def test_login_invalid_credentials(
    api_client,
    login_payload,
) -> None:
    payload = login_payload.model_dump()
    payload["password"] = "WrongPassword123"

    with patch(
        "app.routers.auth.AuthService.login",
        new_callable=AsyncMock,
        side_effect=InvalidCredentialsError(),
    ) as mock_login:
        response = await api_client.post(
            "/auth/login",
            json=payload,
        )

    assert response.status_code == 401

    mock_login.assert_awaited_once()

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 401
    assert body["message"] == "Invalid email or password"
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_login_invalid_email(
    api_client,
    login_payload,
) -> None:
    payload = login_payload.model_dump()
    payload["email"] = "invalid-email"

    with patch(
        "app.routers.auth.AuthService.login",
        new_callable=AsyncMock,
    ) as mock_login:
        response = await api_client.post(
            "/auth/login",
            json=payload,
        )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 422
    assert body["message"] == "Validation failed"
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_INPUT"
    assert isinstance(body["error"]["details"], list)

    mock_login.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_missing_password(
    api_client,
    login_payload,
) -> None:
    payload = login_payload.model_dump()
    del payload["password"]

    with patch(
        "app.routers.auth.AuthService.login",
        new_callable=AsyncMock,
    ) as mock_login:
        response = await api_client.post(
            "/auth/login",
            json=payload,
        )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 422
    assert body["message"] == "Validation failed"
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_INPUT"
    assert isinstance(body["error"]["details"], list)

    mock_login.assert_not_awaited()
