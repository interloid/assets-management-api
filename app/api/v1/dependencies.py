from typing import Annotated, Any
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Response, status

from app.api.deps import DBSession, RedisClient
from app.api.v1.cookies import set_auth_cookies
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
from app.modules.auth.services import AuthService
from app.modules.user.models import User
from app.modules.user.repositories import UserRepository
from app.shared.models.enums import UserRole

RefreshToken = Annotated[
    str | None,
    Cookie(alias="refresh_token"),
]

AccessToken = Annotated[str | None, Cookie(alias="access_token")]


async def _get_user_from_access_token(
    session: DBSession,
    redis_client: RedisClient,
    access_token: AccessToken,
):
    try:
        payload = decode_access_token(access_token)
    except InvalidAccessTokenError:
        return None

    try:
        user_id = UUID(payload["sub"])
        token_version = int(payload["token_version"])
        family_id = UUID(payload["family_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError() from exc

    if await is_access_token_family_blacklisted(redis_client, family_id):
        raise InvalidAccessTokenError()

    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)

    if user is None or token_version != user.token_version:
        raise InvalidAccessTokenError()

    if not user.is_active:
        raise UserInactiveError()

    return user


async def _get_user_from_refresh_token(
    session: DBSession,
    response: Response,
    refresh_token: RefreshToken,
):
    auth_service = AuthService(session)

    try:
        new_access_token, new_refresh_token = await auth_service.refresh(refresh_token)
    except Exception as exc:
        raise InvalidAccessTokenError() from exc

    set_auth_cookies(
        response,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )

    new_payload = decode_access_token(new_access_token)
    user_id = UUID(new_payload["sub"])

    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise UserInactiveError()

    return user


async def get_current_user(
    session: DBSession,
    redis_client: RedisClient,
    response: Response,
    access_token: AccessToken = None,
    refresh_token: RefreshToken = None,
):
    if access_token is not None:
        user = await _get_user_from_access_token(
            session,
            redis_client,
            access_token,
        )

        if user is not None:
            return user

    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await _get_user_from_refresh_token(
        session,
        response,
        refresh_token,
    )


def get_logout_access_token(
    access_token: AccessToken = None,
) -> dict[str, Any] | None:
    if access_token is None:
        return None

    payload = decode_access_token_allow_expired(access_token)

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
    access_token: AccessToken = None,
) -> dict[str, Any]:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = access_token

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


CurrentUser = Annotated[
    User | None,
    Depends(get_current_user),
]

AdminUser = Annotated[
    User,
    Depends(require_admin),
]


LogoutAccessTokenPayload = Annotated[
    dict[str, Any] | None,
    Depends(get_logout_access_token),
]

LogoutAllContext = Annotated[
    dict[str, Any] | None,
    Depends(get_logout_all_context),
]
