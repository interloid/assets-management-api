from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.redis import get_token_version, set_token_version
from app.db.session import get_db
from app.dependencies.redis import get_redis
from app.exceptions.auth import InvalidTokenError, UserInactiveError
from app.repositories.user import UserRepository
from app.services.jwt_blacklist import is_access_token_blacklisted

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])

        jti = payload["jti"]

        token_version = int(payload["token_version"])

    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError() from exc

    if await is_access_token_blacklisted(
        redis_client,
        jti,
    ):
        raise InvalidTokenError()

    current_token_version = await get_token_version(redis_client, str(user_id))

    user = None

    if current_token_version is None:
        repository = UserRepository(session)

        user = await repository.get_by_id(user_id)

        if user is None:
            raise InvalidTokenError()

        current_token_version = user.token_version

        await set_token_version(
            redis_client,
            str(user_id),
            current_token_version,
        )

    if token_version != current_token_version:
        raise InvalidTokenError()

    if user is None:
        repository = UserRepository(session)

        user = await repository.get_by_id(user_id)

        if user is None:
            raise InvalidTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return user


def get_current_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, any]:
    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        payload["jti"]
        payload["exp"]
    except (KeyError, TypeError) as exc:
        raise InvalidTokenError() from exc

    return payload
