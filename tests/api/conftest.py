from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import generate_refresh_token, hash_refresh_token
from app.main import app
from app.models.refresh_token import RefreshToken


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def create_refresh_token(
    db_session,
    active_user,
):
    async def _create(
        *,
        expired: bool = False,
        revoked: bool = False,
    ):
        raw_token = generate_refresh_token()

        now = datetime.now(timezone.utc)

        expires_at = now - timedelta(days=1) if expired else now + timedelta(days=7)

        refresh_token = RefreshToken(
            user_id=active_user.id,
            token_hash=hash_refresh_token(raw_token),
            family_id=uuid4(),
            expires_at=expires_at,
            revoked_at=now if revoked else None,
        )

        db_session.add(refresh_token)

        await db_session.commit()
        await db_session.refresh(refresh_token)

        return raw_token, refresh_token

    return _create
