from fastapi import APIRouter, Response, status

from app.api.deps import DBSession, RedisClient
from app.api.v1.dependencies import (
    LogoutAccessTokenPayload,
    LogoutAllContext,
    RefreshToken,
)
from app.api.v1.responses import (
    CONFLICT_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    LOGOUT_UNAUTHORIZED_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.core.config import settings
from app.modules.auth.services import AuthService
from app.shared.schemas.common import SuccessResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

ACCESS_TOKEN_COOKIE_PATH = "/"
REFRESH_TOKEN_COOKIE_PATH = "/"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        **CONFLICT_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def register(
    data: RegisterRequest,
    session: DBSession,
) -> SuccessResponse[UserResponse]:
    service = AuthService(session)

    user = await service.register(
        email=str(data.email),
        password=data.password,
        full_name=data.full_name,
    )

    return SuccessResponse(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def login(
    response: Response,
    payload: LoginRequest,
    session: DBSession,
):
    service = AuthService(session)

    access_token, refresh_token = await service.login(
        email=payload.email,
        password=payload.password,
    )

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="none",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=ACCESS_TOKEN_COOKIE_PATH,
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )

    return SuccessResponse(data={"message": "Login successful"})


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def refresh(
    response: Response,
    session: DBSession,
    refresh_token: RefreshToken = None,
):
    service = AuthService(session)

    access_token, new_refresh_token = await service.refresh(refresh_token)

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="none",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=ACCESS_TOKEN_COOKIE_PATH,
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )

    return SuccessResponse(data={"message": "Token refreshed successfully"})


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **LOGOUT_UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def logout(
    response: Response,
    session: DBSession,
    access_token: LogoutAccessTokenPayload,
    refresh_token: RefreshToken = None,
    redis_client: RedisClient = None,
) -> None:
    service = AuthService(session)

    await service.logout(refresh_token, access_token, redis_client)

    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path=ACCESS_TOKEN_COOKIE_PATH,
    )

    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def logout_all(
    response: Response,
    session: DBSession,
    logout_all_context: LogoutAllContext,
) -> None:
    service = AuthService(session)

    await service.logout_all(
        logout_all_context["user"],
        logout_all_context["token_version"],
    )

    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path=ACCESS_TOKEN_COOKIE_PATH,
    )

    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )
