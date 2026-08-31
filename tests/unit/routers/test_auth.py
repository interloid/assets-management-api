from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.exceptions.auth import EmailAlreadyRegisteredError
from app.models.enums import UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_register_returns_409_when_email_already_registered(
    async_client,
    user_payload,
) -> None:
    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
        side_effect=EmailAlreadyRegisteredError,
    ):
        response = await async_client.post(
            "/auth/register",
            json=user_payload,
        )

    assert response.status_code == 409

    assert response.json() == {
        "detail": "Email already registered",
    }


@pytest.mark.asyncio
async def test_register_returns_created_user(
    async_client,
    user_payload,
) -> None:
    created_user = User(
        id=uuid4(),
        email=user_payload["email"],
        password_hash="hashed-password",
        full_name=user_payload["full_name"],
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.routers.auth.AuthService.register",
        new_callable=AsyncMock,
        return_value=created_user,
    ):
        response = await async_client.post(
            "/auth/register",
            json=user_payload,
        )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == str(created_user.id)
    assert body["email"] == user_payload["email"]
    assert body["full_name"] == user_payload["full_name"]
    assert body["role"] == "user"
    assert body["is_active"] is True
