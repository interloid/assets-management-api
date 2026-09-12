import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db


@pytest.mark.asyncio
async def test_session_factory_creates_async_session() -> None:
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)


@pytest.mark.asyncio
async def test_get_db_yields_session() -> None:
    generator = get_db()

    session = await anext(generator)

    try:
        assert isinstance(session, AsyncSession)
    finally:
        await generator.aclose()
