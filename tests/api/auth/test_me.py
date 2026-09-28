from unittest.mock import patch

import pytest

from app.api.v1.dependencies import get_current_user
from app.main import app
from app.modules.auth.exceptions import InvalidTokenError


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

    assert body["error"]["message"] == "Authentication credentials were not provided"
    assert body["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_me_invalid_jwt(
    api_client,
) -> None:
    with patch(
        "app.api.v1.dependencies.decode_access_token",
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

    assert body["error"]["message"] == "Invalid or expired token"
    assert body["error"]["code"] == "INVALID_TOKEN"
