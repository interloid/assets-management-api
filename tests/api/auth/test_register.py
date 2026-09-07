from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.auth import EmailAlreadyRegisteredError


@pytest.mark.asyncio
async def test_valid_registration(
    api_client,
    user_payload,
    user,
) -> None:
    response_user = user

    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
        return_value=response_user,
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
            json=user_payload,
        )

    assert response.status_code == 201

    mock_register.assert_awaited_once()

    body = response.json()

    assert body["success"] is True
    assert body["statusCode"] == 201
    assert body["message"] == "User registered successfully"
    assert body["error"] is None

    data = body["data"]

    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name
    assert data["role"] == user.role.value
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_duplicate_email(
    api_client,
    user_payload,
) -> None:
    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
        side_effect=EmailAlreadyRegisteredError(),
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
            json=user_payload,
        )

    assert response.status_code == 409

    mock_register.assert_awaited_once()

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 409
    assert body["message"] == "Email is already registered"
    assert body["data"] is None
    assert body["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_invalid_email(
    api_client,
    user_payload,
) -> None:
    payload = user_payload.copy()
    payload["email"] = "invalid-email"

    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
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

    mock_register.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_field(
    api_client,
    user_payload,
) -> None:
    payload = user_payload.copy()
    del payload["full_name"]

    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
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

    mock_register.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_password(
    api_client,
    user_payload,
) -> None:
    payload = user_payload.copy()
    payload["password"] = "password"

    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
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

    mock_register.assert_not_awaited()
