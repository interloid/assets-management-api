from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.system import ServiceStatus


async def check_dependencies(
    db: AsyncSession, redis: Redis
) -> dict[str, ServiceStatus]:
    results: dict[str, ServiceStatus] = {}

    try:
        await db.execute(text("SELECT 1"))
        results["database"] = ServiceStatus(status="ok")
    except Exception:
        results["database"] = ServiceStatus(status="down")

    try:
        await redis.ping()
        results["redis"] = ServiceStatus(status="ok")
    except Exception:
        results["redis"] = ServiceStatus(status="down")

    return results
