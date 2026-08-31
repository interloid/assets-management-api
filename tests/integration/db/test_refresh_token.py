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
    """DB-REFRESH-02: Refresh token hash is stored, not the raw token."""

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
async def test_refresh_token_seven_day_expiry(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    """DB-REFRESH-03: Refresh token expires approximately 7 days later."""

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
    """DB-REFRESH-04: Refresh token has a family ID."""

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
