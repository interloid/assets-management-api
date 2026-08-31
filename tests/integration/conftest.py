from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from uuid6 import uuid7

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


@pytest_asyncio.fixture
async def integration_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        settings.test_database_url,
        echo=False,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            # Reset the session if the test caused an IntegrityError.
            await session.rollback()

            # Clean all test data.
            await session.execute(
                text(
                    """
                    TRUNCATE TABLE
                        refresh_tokens,
                        assets,
                        users
                    RESTART IDENTITY CASCADE
                    """
                )
            )

            await session.commit()

    await engine.dispose()


async def create_test_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        email="asset-owner@example.com",
        password_hash="hashed-password",
        full_name="Asset Owner",
    )

    db_session.add(user)
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def integration_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        email=f"refresh-test-{uuid7()}@example.com",
        password_hash="hashed-password",
        full_name="Refresh Token Test User",
        role=UserRole.USER,
        is_active=True,
    )

    db_session.add(user)
    await db_session.flush()

    return user
