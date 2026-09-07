from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.responses import success_response
from app.dependencies.redis import RedisClient
from app.dependencies.types import (
    AccessTokenPayload,
    CurrentUser,
    DBSession,
    RefreshToken,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    session: DBSession,
):

    service = AuthService(session)

    user = await service.register(data)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully",
        data=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    payload: LoginRequest,
    session: DBSession,
    redis_client: RedisClient,
):
    service = AuthService(session)

    result = await service.login(
        payload,
        redis_client,
    )

    data = LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )

    response = success_response(
        status_code=status.HTTP_200_OK,
        message="Login successful",
        data=data.model_dump(mode="json"),
    )

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return response


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
async def refresh(
    session: DBSession,
    refresh_token: RefreshToken = None,
):
    service = AuthService(session)

    result = await service.refresh(refresh_token)

    data = LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )

    response = success_response(
        status_code=status.HTTP_200_OK,
        message="Token refreshed successfully",
        data=data.model_dump(mode="json"),
    )

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",
    )

    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response,
    session: DBSession,
    access_token: AccessTokenPayload,
    refresh_token: RefreshToken = None,
    redis_client: RedisClient = None,
) -> None:
    service = AuthService(session)

    await service.logout(refresh_token, access_token, redis_client)

    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="lax"
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(
    response: Response,
    session: DBSession,
    current_user: CurrentUser,
    redis_client: RedisClient,
    refresh_token: RefreshToken = None,
) -> None:
    service = AuthService(session)

    await service.logout_all(refresh_token, current_user, redis_client)

    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="lax"
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: CurrentUser,
):
    return success_response(
        status_code=status.HTTP_200_OK,
        message="User retrieved successfully",
        data=UserResponse.model_validate(current_user).model_dump(
            mode="json",
        ),
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DBSession,
    redis_client: RedisClient,
):
    service = AuthService(session)

    await service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
        redis_client=redis_client,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Password changed successfully",
        data=None,
    )
