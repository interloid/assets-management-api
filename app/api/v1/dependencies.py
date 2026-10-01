from typing import Annotated, Any
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import DBSession, RedisClient
from app.core.exceptions import InvalidAccessTokenError
from app.core.security import (
    decode_access_token,
    decode_access_token_allow_expired,
    validate_logout_token_expiry,
)
from app.modules.auth.exceptions import (
    AuthorizationError,
    UserInactiveError,
)
from app.modules.auth.jwt_blacklist import (
    is_access_token_family_blacklisted,
)
from app.modules.user.models import User
from app.modules.user.repositories import UserRepository
from app.shared.models.enums import UserRole

security = HTTPBearer(auto_error=False, bearerFormat="JWT")


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
        token_version = int(payload["token_version"])
        family_id = payload["family_id"]

    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError() from exc

    if await is_access_token_family_blacklisted(
        redis_client,
        family_id,
    ):
        raise InvalidAccessTokenError()

    repository = UserRepository(session)

    user = await repository.get_by_id(user_id)

    if user is None:
        raise InvalidAccessTokenError()

    if token_version != user.token_version:
        raise InvalidAccessTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return user


def get_logout_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    if credentials is None:
        return None

    payload = decode_access_token_allow_expired(credentials.credentials)

    try:
        payload["jti"]
        exp = payload["exp"]
        payload["family_id"]
    except (KeyError, TypeError) as exc:
        raise InvalidAccessTokenError() from exc

    validate_logout_token_expiry(exp)

    return payload


async def get_logout_all_context(
    session: DBSession,
    redis_client: RedisClient,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    payload = decode_access_token_allow_expired(token)

    try:
        user_id = UUID(payload["sub"])
        token_version = int(payload["token_version"])
        exp = payload["exp"]
        family_id = payload["family_id"]
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError() from exc

    validate_logout_token_expiry(exp)

    if await is_access_token_family_blacklisted(
        redis_client,
        family_id,
    ):
        raise InvalidAccessTokenError()

    repository = UserRepository(session)

    user = await repository.get_by_id(user_id)

    if user is None:
        raise InvalidAccessTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return {
        "user": user,
        "token_version": token_version,
        "family_id": payload["family_id"],
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
    dict[str, Any] | None,
    Depends(get_logout_all_context),
]
