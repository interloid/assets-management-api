from redis.asyncio import Redis

BLACKLIST_PREFIX = "blacklist:access:"


def _blacklist_key(jti: str) -> str:
    return f"{BLACKLIST_PREFIX}{jti}"


async def blacklist_access_token(
    redis_client: Redis,
    jti: str,
    expires_in: int,
) -> None:
    if expires_in <= 0:
        return

    await redis_client.set(
        _blacklist_key(jti),
        "1",
        ex=expires_in,
    )


async def is_access_token_blacklisted(
    redis_client: Redis,
    jti: str,
) -> bool:
    return bool(await redis_client.exists(_blacklist_key(jti)))
