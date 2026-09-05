from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.user import User
from tests.config import test_settings


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        str(test_settings.TEST_DATABASE_URL),
        echo=False,
    )

    async with engine.connect() as connection:
        transaction = await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            await connection.begin_nested()

            yield session

            await session.rollback()

        await transaction.rollback()

    await engine.dispose()


async def create_test_user(db_session: AsyncSession) -> User:
    user = User(
        email="asset-owner@example.com",
        password_hash="hashed-password",
        full_name="Asset Owner",
    )

    db_session.add(user)
    await db_session.flush()

    return user
