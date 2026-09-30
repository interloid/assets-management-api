from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    return Redis.from_url(
        str(settings.REDIS_URL),
        decode_responses=True,
    )
