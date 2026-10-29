from fastapi import Response

from app.core.config import settings

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

COOKIE_PATH = "/"


def _secure() -> bool:
    return settings.ENVIRONMENT == "production"


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=_secure(),
        samesite="none",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=COOKIE_PATH,
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=_secure(),
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    for key in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        response.delete_cookie(
            key=key,
            httponly=True,
            secure=_secure(),
            samesite="none",
            path=COOKIE_PATH,
        )
