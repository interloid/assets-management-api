from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.dependencies.types import CurrentUser, DBSession, RefreshToken
from app.schemas.auth import (
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
) -> UserResponse:

    service = AuthService(session)

    user = await service.register(data)

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    payload: LoginRequest,
    response: Response,
    session: DBSession,
) -> LoginResponse:
    service = AuthService(session)

    result = await service.login(payload)

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expiry_days * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
async def refresh(
    response: Response,
    session: DBSession,
    refresh_token: RefreshToken = None,
) -> LoginResponse:
    service = AuthService(session)

    result = await service.refresh(refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expiry_days * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=result.access_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response, session: DBSession, refresh_token: RefreshToken = None
):
    service = AuthService(session)

    await service.logout(refresh_token)

    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="lax"
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(
    response: Response, session: DBSession, refresh_token: RefreshToken = None
):
    service = AuthService(session)

    await service.logout_all(refresh_token)

    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="lax"
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)
