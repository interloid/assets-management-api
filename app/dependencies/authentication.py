from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
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

    repository = UserRepository(session)

    user = await repository.get_by_id(user_id)

    if user is None:
        raise InvalidTokenError()

    if token_version != user.token_version:
        raise InvalidTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return user


async def get_current_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: Redis = Depends(get_redis),
) -> dict[str, Any]:
    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        jti = payload["jti"]
        payload["exp"]
    except (KeyError, TypeError) as exc:
        raise InvalidTokenError() from exc

    if await is_access_token_blacklisted(
        redis_client,
        jti,
    ):
        raise InvalidTokenError()

    return payload


def get_logout_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        payload["jti"]
        payload["exp"]
    except (KeyError, TypeError) as exc:
        raise InvalidTokenError() from exc

    return payload


async def get_logout_all_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])
        token_version = int(payload["token_version"])
        payload["jti"]
        payload["exp"]
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError() from exc

    repository = UserRepository(session)

    user = await repository.get_by_id(user_id)

    if user is None:
        raise InvalidTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return {
        "user": user,
        "token_version": token_version,
    }
