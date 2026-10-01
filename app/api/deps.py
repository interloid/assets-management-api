from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


RedisClient = Annotated[
    Redis,
    Depends(get_redis),
]
