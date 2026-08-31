from fastapi import APIRouter, HTTPException, status

from app.dependencies.types import DBSession
from app.exceptions.auth import EmailAlreadyRegisteredError
from app.schemas.auth import RegisterRequest, UserResponse
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


