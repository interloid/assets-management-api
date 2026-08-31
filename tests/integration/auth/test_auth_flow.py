import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.mark.asyncio
async def test_register_then_login(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:

    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    register_body = register_response.json()

    assert register_body["email"] == user_payload["email"]
    assert register_body["full_name"] == user_payload["full_name"]
    assert register_body["role"] == "user"
    assert register_body["is_active"] is True

    user_id = register_body["id"]

    result = await db_session.execute(select(User).where(User.id == user_id))

    user = result.scalar_one()

    assert user.email == user_payload["email"]
    assert user.full_name == user_payload["full_name"]
    assert user.password_hash != user_payload["password"]

    login_response = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    login_body = login_response.json()

    assert login_body["access_token"]
    assert login_body["token_type"] == "bearer"

    assert "refresh_token" not in login_body

    assert "refresh_token" in login_response.cookies

    refresh_token = login_response.cookies["refresh_token"]

    assert refresh_token
    assert len(refresh_token) > 0

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )

    persisted_refresh_token = result.scalar_one()

    assert persisted_refresh_token.user_id == user.id
    assert persisted_refresh_token.token_hash != refresh_token
    assert persisted_refresh_token.family_id is not None
    assert persisted_refresh_token.expires_at is not None
    assert persisted_refresh_token.revoked_at is None
