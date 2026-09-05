from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_user_defaults_are_generated(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="defaults@example.com",
        password_hash="hashed-password",
        full_name="Defaults Test",
        role=UserRole.USER,
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert isinstance(user.id, UUID)
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_user_default_values(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="default-values@example.com",
        password_hash="hashed-password",
        full_name="Default Values",
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.role == UserRole.USER
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_email_cannot_be_null(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=None,
        password_hash="hashed-password",
        full_name="Test User",
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_password_hash_cannot_be_null(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="null-password@example.com",
        password_hash=None,
        full_name="Test User",
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_full_name_cannot_be_null(
    db_session: AsyncSession,
) -> None:
    user = User(
        email="null-name@example.com",
        password_hash="hashed-password",
        full_name=None,
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        await db_session.flush()
