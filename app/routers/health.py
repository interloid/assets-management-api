from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.dependencies.redis import RedisClient
from app.dependencies.types import DBSession

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health_check(
    db: DBSession,
    redis: RedisClient,
) -> JSONResponse:
    database_status = "up"
    redis_status = "up"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "down"

    try:
        await redis.ping()
    except Exception:
        redis_status = "down"

    is_ready = database_status == "up" and redis_status == "up"

    return JSONResponse(
        status_code=(
            status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content={
            "status": "ready" if is_ready else "not ready",
            "services": {
                "database": database_status,
                "redis": redis_status,
            },
        },
    )
