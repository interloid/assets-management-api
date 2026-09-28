from fastapi import APIRouter, Response, status

from app.constants.response import (
    CONFLICT_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.core.config import settings
from app.core.responses import success_response
from app.dependencies.redis import RedisClient
from app.dependencies.types import (
    CurrentUser,
    DBSession,
    LogoutAccessTokenPayload,
    LogoutAllContext,
    RefreshToken,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.schemas.common import SuccessResponse
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

COOKIE_PATH = "/auth"


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

    user = await service.register(data)

    return success_response(
        status_code=status.HTTP_201_CREATED,
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
    payload: LoginRequest,
    session: DBSession,
) -> SuccessResponse[LoginResponse]:
    service = AuthService(session)

    result = await service.login(
        payload,
    )

    data = LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )

    response = success_response(
        status_code=status.HTTP_200_OK,
        data=data.model_dump(mode="json"),
    )

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=COOKIE_PATH,
    )

    return response


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
    session: DBSession,
    refresh_token: RefreshToken = None,
) -> SuccessResponse[LoginResponse]:
    service = AuthService(session)

    result = await service.refresh(refresh_token)

    data = LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )

    response = success_response(
        status_code=status.HTTP_200_OK,
        data=data.model_dump(mode="json"),
    )

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=COOKIE_PATH,
    )

    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
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
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
        path=COOKIE_PATH,
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
    refresh_token: RefreshToken = None,
) -> None:
    service = AuthService(session)

    await service.logout_all(
        refresh_token,
        logout_all_context["user"],
        logout_all_context["token_version"],
    )

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
        path=COOKIE_PATH,
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_me(
    current_user: CurrentUser,
) -> SuccessResponse[UserResponse]:
    return success_response(
        status_code=status.HTTP_200_OK,
        data=UserResponse.model_validate(current_user).model_dump(
            mode="json",
        ),
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DBSession,
) -> SuccessResponse[None]:
    service = AuthService(session)

    await service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=None,
    )
