import asyncio

from app.db.redis import redis_client
from app.services.jwt_blacklist import (
    blacklist_access_token,
    is_access_token_blacklisted,
)


async def main() -> None:
    jti = "test-jti-123"

    print(
        "Before:",
        await is_access_token_blacklisted(jti),
    )

    await blacklist_access_token(
        jti=jti,
        expires_in=30,
    )

    print(
        "After:",
        await is_access_token_blacklisted(jti),
    )

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
