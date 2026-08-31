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

    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["full_name"] == user.full_name
    assert body["role"] == user.role.value
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_duplicate_email(
    api_client,
    user_payload,
) -> None:
    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
        side_effect=EmailAlreadyRegisteredError,
    ) as mock_register:
        response = await api_client.post(
            "/auth/register",
            json=user_payload,
        )

    assert response.status_code == 409

    assert response.json()["detail"] == "Email already registered"

    mock_register.assert_awaited_once()


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

    mock_register.assert_not_awaited()
