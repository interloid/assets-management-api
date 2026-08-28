import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.user import User


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(
        settings.test_database_url,
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
