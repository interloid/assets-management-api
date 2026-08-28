from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.models.refresh_token import RefreshToken
from tests.integration.conftest import create_test_user


@pytest.mark.asyncio
async def test_create_refresh_token(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="test-token-hash-001",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(refresh_token)
    await db_session.flush()

    assert refresh_token.id is not None
    assert refresh_token.user_id == user.id
    assert refresh_token.token_hash == "test-token-hash-001"
    assert refresh_token.family_id is not None
    assert refresh_token.expires_at is not None
    assert refresh_token.revoked_at is None
    assert refresh_token.created_at is not None


@pytest.mark.asyncio
async def test_refresh_token_belongs_to_user(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="test-token-hash-002",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(refresh_token)
    await db_session.flush()

    assert refresh_token.user_id == user.id


@pytest.mark.asyncio
async def test_refresh_token_invalid_user_id_rejected(
    db_session: AsyncSession,
) -> None:
    refresh_token = RefreshToken(
        user_id=uuid7(),
        token_hash="test-token-hash-003",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(refresh_token)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_refresh_token_hash_must_be_unique(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    token_1 = RefreshToken(
        user_id=user.id,
        token_hash="duplicate-hash",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(token_1)
    await db_session.flush()

    token_2 = RefreshToken(
        user_id=user.id,
        token_hash="duplicate-hash",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(token_2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_refresh_token_can_be_revoked(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="test-token-hash-004",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(refresh_token)
    await db_session.flush()

    assert refresh_token.revoked_at is None

    revoked_at = datetime.now(UTC)
    refresh_token.revoked_at = revoked_at

    await db_session.flush()
    await db_session.refresh(refresh_token)

    assert refresh_token.revoked_at is not None


@pytest.mark.asyncio
async def test_refresh_token_created_at_is_set(
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="test-token-hash-005",
        family_id=uuid7(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db_session.add(refresh_token)
    await db_session.flush()

    assert refresh_token.created_at is not None
