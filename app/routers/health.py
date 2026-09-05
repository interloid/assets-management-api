from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.dependencies.redis import RedisClient
from app.dependencies.types import DBSession

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/db")
async def database_health(
    db: DBSession,
) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc

    return {
        "status": "healthy",
        "service": "database",
    }


@router.get("/redis")
async def redis_health(
    redis: RedisClient,
) -> dict[str, str]:
    try:
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        ) from exc

    return {
        "status": "healthy",
        "service": "redis",
    }


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "api",
    }
