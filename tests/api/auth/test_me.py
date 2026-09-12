from unittest.mock import patch

import pytest

from app.dependencies.authentication import get_current_user
from app.exceptions.auth import InvalidTokenError
from app.main import app


@pytest.mark.asyncio
async def test_me_success(
    api_client,
    user,
) -> None:
    async def mock_current_user():
        return user

    app.dependency_overrides[get_current_user] = mock_current_user

    try:
        response = await api_client.get(
            "/auth/me",
        )

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["statusCode"] == 200
    assert body["message"] == "User retrieved successfully"
    assert body["error"] is None

    data = body["data"]

    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name
    assert data["role"] == user.role.value
    assert "created_at" in data


@pytest.mark.asyncio
async def test_me_missing_jwt(
    api_client,
) -> None:
    response = await api_client.get(
        "/auth/me",
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 401
    assert body["message"] == "Authentication required"
    assert body["data"] is None
    assert body["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert body["error"]["details"] == ("Authentication credentials were not provided")


@pytest.mark.asyncio
async def test_me_invalid_jwt(
    api_client,
) -> None:
    with patch(
        "app.dependencies.authentication.decode_access_token",
        side_effect=InvalidTokenError(),
    ):
        response = await api_client.get(
            "/auth/me",
            headers={
                "Authorization": "Bearer invalid-access-token",
            },
        )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 401
    assert body["message"] == "Invalid or expired token"
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_TOKEN"
    assert body["error"]["details"] is None
