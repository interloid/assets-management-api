from math import ceil

from fastapi import APIRouter, Query, status

from app.core.responses import success_response
from app.dependencies.types import AdminUser, DBSession
from app.schemas.auth import UserListResponse
from app.schemas.common import ErrorResponse, PaginationMeta, SuccessResponse
from app.services.users import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials are invalid or missing",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Admin access is required",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Request validation failed",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def list_users(
    session: DBSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> SuccessResponse[list[UserListResponse]]:
    service = UserService(session)

    users, total = await service.list_users(
        page=page,
        size=size,
        search=search,
    )

    data = [
        UserListResponse.model_validate(user).model_dump(mode="json") for user in users
    ]

    total_pages = ceil(total / size) if total else 0

    meta = PaginationMeta(
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total,
    ).model_dump(mode="json")

    return success_response(
        status_code=status.HTTP_200_OK,
        data=data,
        meta=meta,
    )
