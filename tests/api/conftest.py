from collections.abc import AsyncGenerator
from itertools import count

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from uuid6 import uuid7

import app.shared.models.registry  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.database import get_db
from app.main import app
from app.modules.user.models import User
from app.shared.models.enums import UserRole
from tests.config import test_settings

_test_client_ips = count(1)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        str(test_settings.TEST_DATABASE_URL),
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
            await session.rollback()

            await session.execute(
                text(
                    """
                    TRUNCATE TABLE
                        refresh_tokens,
                        asset_tag_counters,
                        assets,
                        users,
                        background_jobs,
                        asset_assignments,
                        asset_exports,
                        asset_files
                    RESTART IDENTITY CASCADE
                    """
                )
            )

            await session.commit()

    await engine.dispose()


@pytest_asyncio.fixture
async def integration_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    client_ip = f"127.0.0.{next(_test_client_ips)}"

    try:
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(
                    app=app,
                    client=(client_ip, 12345),
                ),
                base_url="http://test",
            ) as client:
                yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def create_test_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        email=f"asset-owner-{uuid7()}@example.com",
        password_hash="hashed-password",
        full_name="Asset Owner",
        role=UserRole.USER,
        is_active=True,
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


@pytest_asyncio.fixture
async def integration_admin(
    db_session: AsyncSession,
) -> User:
    admin = User(
        email=f"asset-admin-{uuid7()}@example.com",
        password_hash="hashed-password",
        full_name="Asset Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(admin)
    await db_session.flush()

    return admin


@pytest_asyncio.fixture
async def admin_access_token(
    integration_admin: User,
) -> str:
    return create_access_token(
        user_id=str(integration_admin.id),
        role=integration_admin.role.value,
        token_version=integration_admin.token_version,
        family_id=str(uuid7()),
    )


@pytest_asyncio.fixture
async def asset_owner(
    db_session: AsyncSession,
) -> User:
    return await create_test_user(db_session)


@pytest_asyncio.fixture
async def authenticated_client(
    integration_client: AsyncClient,
    user_payload: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    await integration_client.post(
        "/api/v1/auth/register",
        json=user_payload,
    )

    response = await integration_client.post(
        "/api/v1/auth/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert response.status_code == 200

    access_token = response.cookies["access_token"]

    integration_client.cookies.set("access_token", access_token)

    yield integration_client
