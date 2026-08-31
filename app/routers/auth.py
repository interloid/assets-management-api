from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import settings
from app.dependencies.types import DBSession
from app.exceptions.auth import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
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

    try:
        user = await service.register(data)

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

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
    try:
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

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )
