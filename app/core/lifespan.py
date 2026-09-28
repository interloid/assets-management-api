from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import engine
from app.core.redis import create_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis_client()

    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
