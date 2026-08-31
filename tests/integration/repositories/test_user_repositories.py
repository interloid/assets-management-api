import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_get_by_email_returns_user(
    db_session,
) -> None:
    user = User(
        email="user@example.com",
        password_hash="hash",
        full_name="Test User",
    )

    db_session.add(user)
    await db_session.commit()

    repository = UserRepository(db_session)

    result = await repository.get_by_email("user@example.com")

    assert result is not None
    assert result.email == "user@example.com"


@pytest.mark.asyncio
async def test_email_is_unique_case_insensitively(
    db_session,
) -> None:
    first_user = User(
        email="user@example.com",
        password_hash="hash1",
        full_name="User One",
    )

    db_session.add(first_user)
    await db_session.commit()

    second_user = User(
        email="USER@EXAMPLE.COM",
        password_hash="hash2",
        full_name="User Two",
    )

    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_create_returns_created_user(
    db_session,
) -> None:
    repository = UserRepository(db_session)

    result = await repository.create(
        email="test@example.com",
        password_hash="hashed-password",
        full_name="Test User",
    )

    assert result.email == "test@example.com"
    assert result.password_hash == "hashed-password"
    assert result.full_name == "Test User"
