from redis.asyncio import Redis

FAMILY_BLACKLIST_PREFIX = "blacklist:family:"


def _family_blacklist_key(family_id: str) -> str:
    return f"{FAMILY_BLACKLIST_PREFIX}{family_id}"


async def blacklist_access_token_family(
    redis_client: Redis,
    family_id: str,
    expires_in: int,
) -> None:
    if expires_in <= 0:
        return

    await redis_client.set(
        _family_blacklist_key(family_id),
        "1",
        ex=expires_in,
    )


async def is_access_token_family_blacklisted(
    redis_client: Redis,
    family_id: str,
) -> bool:
    return bool(
        await redis_client.exists(
            _family_blacklist_key(family_id),
        )
    )
