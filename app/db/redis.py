from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    return Redis.from_url(
        str(settings.REDIS_URL),
        decode_responses=True,
    )


TOKEN_VERSION_PREFIX = "auth:token_version"


def token_version_key(user_id: str) -> str:
    return f"{TOKEN_VERSION_PREFIX}:{user_id}"


async def get_token_version(redis, user_id: str) -> int | None:
    value = await redis.get(token_version_key(user_id))

    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.decode()

    return int(value)


async def set_token_version(
    redis,
    user_id: str,
    version: int,
) -> None:
    await redis.set(
        token_version_key(user_id),
        version,
    )
