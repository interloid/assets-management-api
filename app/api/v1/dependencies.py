from typing import Annotated, Any
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import DBSession, RedisClient
from app.core.security import decode_access_token
from app.modules.auth.exceptions import (
    AuthorizationError,
    InvalidTokenError,
    UserInactiveError,
)
from app.modules.auth.jwt_blacklist import is_access_token_blacklisted
from app.modules.user.models import User
from app.modules.user.repositories import UserRepository
from app.shared.models.enums import UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    session: DBSession,
    redis_client: RedisClient,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    payload = decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])
        jti = payload["jti"]
        token_version = int(payload["token_version"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError() from exc

    if await is_access_token_blacklisted(redis_client, jti):
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


def get_logout_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None

    try:
        payload["jti"]
        payload["exp"]
    except (KeyError, TypeError) as exc:
        raise InvalidTokenError() from exc

    return payload


async def get_logout_all_context(
    session: DBSession,
    credentials: HTTPAuthorizationCredentials = Depends(security),
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


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError()

    return current_user


RefreshToken = Annotated[
    str | None,
    Cookie(alias="refresh_token"),
]

CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]

AdminUser = Annotated[
    User,
    Depends(require_admin),
]


LogoutAccessTokenPayload = Annotated[
    dict[str, Any],
    Depends(get_logout_access_token),
]

LogoutAllContext = Annotated[
    dict[str, Any],
    Depends(get_logout_all_context),
]
