from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository


@pytest.mark.asyncio
async def test_refresh_token_persisted(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    repository = RefreshTokenRepository(db_session)

    token_hash = "hashed-refresh-token"
    family_id = uuid7()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    refresh_token = await repository.create(
        user_id=integration_user.id,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=expires_at,
    )

    await db_session.commit()

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.id == refresh_token.id,
        )
    )

    persisted_token = result.scalar_one()

    assert persisted_token.id == refresh_token.id


@pytest.mark.asyncio
async def test_refresh_token_hash_stored(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    repository = RefreshTokenRepository(db_session)

    raw_token = "raw-refresh-token"
    token_hash = "hashed-refresh-token"

    refresh_token = await repository.create(
        user_id=integration_user.id,
        token_hash=token_hash,
        family_id=uuid7(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    await db_session.commit()

    result = await db_session.execute(
        select(RefreshToken.token_hash).where(
            RefreshToken.id == refresh_token.id,
        )
    )

    stored_hash = result.scalar_one()

    assert stored_hash == token_hash
    assert stored_hash != raw_token


@pytest.mark.asyncio
async def test_refresh_token_expiry_stored(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    repository = RefreshTokenRepository(db_session)

    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=7)

    refresh_token = await repository.create(
        user_id=integration_user.id,
        token_hash="hashed-refresh-token",
        family_id=uuid7(),
        expires_at=expires_at,
    )

    await db_session.commit()

    result = await db_session.execute(
        select(RefreshToken.expires_at).where(
            RefreshToken.id == refresh_token.id,
        )
    )

    stored_expires_at = result.scalar_one()

    assert stored_expires_at == expires_at


@pytest.mark.asyncio
async def test_refresh_token_family_id_created(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    repository = RefreshTokenRepository(db_session)

    family_id = uuid7()

    refresh_token = await repository.create(
        user_id=integration_user.id,
        token_hash="hashed-refresh-token",
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    await db_session.commit()

    result = await db_session.execute(
        select(RefreshToken.family_id).where(
            RefreshToken.id == refresh_token.id,
        )
    )

    stored_family_id = result.scalar_one()

    assert stored_family_id == family_id
    assert stored_family_id is not None


@pytest.mark.asyncio
async def test_old_refresh_token_revoked(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    login_response = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    old_token = login_response.cookies["refresh_token"]

    integration_client.cookies.set(
        "refresh_token",
        old_token,
    )

    refresh_response = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response.status_code == 200

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == register_response.json()["id"],
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    revoked_tokens = [token for token in tokens if token.revoked_at is not None]

    assert len(revoked_tokens) == 1


@pytest.mark.asyncio
async def test_refresh_token_family_preserved(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    first_token = login_response.cookies["refresh_token"]

    integration_client.cookies.set(
        "refresh_token",
        first_token,
    )

    refresh_response = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response.status_code == 200

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    family_ids = {token.family_id for token in tokens}

    assert len(family_ids) == 1


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_family(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    old_token = login_response.cookies["refresh_token"]

    integration_client.cookies.set(
        "refresh_token",
        old_token,
    )

    refresh_response = await integration_client.post(
        "/auth/refresh",
    )

    assert refresh_response.status_code == 200

    integration_client.cookies.set(
        "refresh_token",
        old_token,
    )

    reuse_response = await integration_client.post(
        "/auth/refresh",
    )

    assert reuse_response.status_code == 401

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    assert all(token.revoked_at is not None for token in tokens)


@pytest.mark.asyncio
async def test_change_password_revokes_all_refresh_tokens(
    integration_client,
    db_session: AsyncSession,
    user_payload,
) -> None:
    register_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response_1 = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response_1.status_code == 200

    login_response_2 = await integration_client.post(
        "/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response_2.status_code == 200

    access_token = login_response_2.json()["access_token"]

    response = await integration_client.post(
        "/auth/change-password",
        json={
            "current_password": user_payload["password"],
            "new_password": "NewPassword123",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2

    assert all(token.revoked_at is not None for token in tokens)
