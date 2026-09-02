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


@pytest.mark.asyncio
async def test_flow_02_login_then_refresh(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    # Register user
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    # Login
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

    # Refresh token is stored in cookie
    assert "refresh_token" in login_response.cookies

    old_refresh_token = login_response.cookies["refresh_token"]

    # Get persisted refresh token
    result = await db_session.execute(select(RefreshToken))

    stored_tokens = result.scalars().all()

    assert len(stored_tokens) == 1

    old_token_record = stored_tokens[0]

    assert old_token_record.revoked_at is None
    assert old_token_record.token_hash != old_refresh_token
    assert old_token_record.family_id is not None

    # Put refresh token into client's cookie jar
    integration_client.cookies.set(
        "refresh_token",
        old_refresh_token,
    )

    # Refresh
    refresh_response = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response.status_code == 200

    refresh_body = refresh_response.json()

    assert refresh_body["access_token"]
    assert refresh_body["token_type"] == "bearer"

    # Refresh token must NOT be returned in JSON
    assert "refresh_token" not in refresh_body

    # New refresh token must be returned as cookie
    assert "refresh_token" in refresh_response.cookies

    new_refresh_token = refresh_response.cookies["refresh_token"]

    assert new_refresh_token
    assert new_refresh_token != old_refresh_token

    # Verify database rotation
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == old_token_record.user_id)
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    old_token = next(
        token for token in tokens if token.token_hash == old_token_record.token_hash
    )

    new_token = next(
        token for token in tokens if token.token_hash != old_token_record.token_hash
    )

    # Old token is revoked
    assert old_token.revoked_at is not None

    # New token belongs to the same family
    assert new_token.family_id == old_token.family_id

    # New token is active
    assert new_token.revoked_at is None

    # Stored token is hashed
    assert new_token.token_hash != new_refresh_token


@pytest.mark.asyncio
async def test_flow_03_refresh_token_reuse_revokes_family(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    # Register user
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    # Login
    login_response = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    old_refresh_token = login_response.cookies["refresh_token"]

    # Get the original token record for this user
    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    original_token = result.scalar_one()

    family_id = original_token.family_id

    # First refresh → rotates the token
    integration_client.cookies.set(
        "refresh_token",
        old_refresh_token,
    )

    first_refresh_response = await integration_client.post(
        "/auth/refresh",
    )

    assert first_refresh_response.status_code == 200

    new_refresh_token = first_refresh_response.cookies["refresh_token"]

    assert new_refresh_token != old_refresh_token

    # Verify family now contains old + new token
    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
        )
    )

    family_tokens = result.scalars().all()

    assert len(family_tokens) == 2

    assert any(token.revoked_at is not None for token in family_tokens)
    assert any(token.revoked_at is None for token in family_tokens)

    # Reuse the OLD refresh token
    integration_client.cookies.set(
        "refresh_token",
        old_refresh_token,
    )

    reuse_response = await integration_client.post(
        "/auth/refresh",
    )

    assert reuse_response.status_code == 401

    body = reuse_response.json()

    assert body["error"]["code"] == "REFRESH_TOKEN_REUSE"

    # Verify entire family is revoked
    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
        )
    )

    family_tokens = result.scalars().all()

    assert len(family_tokens) == 2

    for token in family_tokens:
        assert token.revoked_at is not None


@pytest.mark.asyncio
async def test_flow_o4_logout_refresh_rejected(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:

    register_reponse = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_reponse.status_code == 201

    user_id = register_reponse.json()["id"]

    login_response = await integration_client.post(
        "auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )

    assert login_response.status_code == 200

    refresh_token = login_response.cookies["refresh_token"]

    integration_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    logout_response = await integration_client.post(
        "/auth/logout",
    )

    assert logout_response.status_code == 204

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    stored_token = result.scalar_one()

    assert stored_token.revoked_at is not None

    integration_client.cookies.set(
        "refresh_token",
        refresh_token,
    )

    refresh_reponse = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_reponse.status_code == 401


@pytest.mark.asyncio
async def test_flow_05_logout_all_all_sessions_rejected(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    # Register user
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    # Login - Session 1
    login_response_1 = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response_1.status_code == 200

    refresh_token_1 = login_response_1.cookies["refresh_token"]

    # Login - Session 2
    login_response_2 = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response_2.status_code == 200

    refresh_token_2 = login_response_2.cookies["refresh_token"]

    # Logout all sessions
    # Set the current refresh token explicitly
    integration_client.cookies.set(
        "refresh_token",
        refresh_token_2,
    )

    # Logout all sessions
    logout_all_response = await integration_client.post(
        "/auth/logout-all",
    )

    assert logout_all_response.status_code == 204

    # Verify both sessions are revoked in the database
    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    for token in tokens:
        assert token.revoked_at is not None

    # Session 1 refresh must fail
    integration_client.cookies.set(
        "refresh_token",
        refresh_token_1,
    )

    refresh_response_1 = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response_1.status_code == 401

    # Session 2 refresh must also fail
    integration_client.cookies.set(
        "refresh_token",
        refresh_token_2,
    )

    refresh_response_2 = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response_2.status_code == 401
