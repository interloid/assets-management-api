from unittest.mock import AsyncMock, patch

import pytest

from app.dependencies.authentication import get_current_user
from app.exceptions.auth import InvalidCredentialsError
from app.main import app


@pytest.mark.asyncio
async def test_change_password_success(
    api_client,
    user,
) -> None:
    payload = {
        "current_password": "OldPassword123",
        "new_password": "NewPassword123",
    }

    async def mock_current_user():
        return user

    app.dependency_overrides[get_current_user] = mock_current_user

    try:
        with patch(
            "app.routers.auth.AuthService.change_password",
            new_callable=AsyncMock,
        ) as mock_change_password:
            response = await api_client.post(
                "/auth/change-password",
                json=payload,
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["data"] is None

    mock_change_password.assert_awaited_once_with(
        user=user,
        current_password=payload["current_password"],
        new_password=payload["new_password"],
    )


@pytest.mark.asyncio
async def test_change_password_wrong_current_password(
    api_client,
    user,
) -> None:
    payload = {
        "current_password": "WrongPassword123",
        "new_password": "NewPassword123",
    }

    async def mock_current_user():
        return user

    app.dependency_overrides[get_current_user] = mock_current_user

    try:
        with patch(
            "app.routers.auth.AuthService.change_password",
            new_callable=AsyncMock,
            side_effect=InvalidCredentialsError(),
        ) as mock_change_password:
            response = await api_client.post(
                "/auth/change-password",
                json=payload,
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    assert response.status_code == 401

    mock_change_password.assert_awaited_once_with(
        user=user,
        current_password=payload["current_password"],
        new_password=payload["new_password"],
    )

    body = response.json()

    assert body["error"]["message"] == "Invalid email or password"
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_change_password_invalid_new_password(
    api_client,
    user,
) -> None:
    payload = {
        "current_password": "OldPassword123",
        "new_password": "short",
    }

    async def mock_current_user():
        return user

    app.dependency_overrides[get_current_user] = mock_current_user

    try:
        with patch(
            "app.routers.auth.AuthService.change_password",
            new_callable=AsyncMock,
        ) as mock_change_password:
            response = await api_client.post(
                "/auth/change-password",
                json=payload,
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["message"] == "Invalid input"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)

    mock_change_password.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_password_unauthenticated(
    api_client,
) -> None:
    payload = {
        "current_password": "OldPassword123",
        "new_password": "NewPassword123",
    }

    with patch(
        "app.routers.auth.AuthService.change_password",
        new_callable=AsyncMock,
    ) as mock_change_password:
        response = await api_client.post(
            "/auth/change-password",
            json=payload,
        )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["message"] == "Authentication credentials were not provided"
    assert body["error"]["code"] == "AUTHENTICATION_REQUIRED"

    mock_change_password.assert_not_awaited()
