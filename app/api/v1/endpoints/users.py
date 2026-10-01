from math import ceil

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DBSession
from app.api.responses import success_response
from app.api.v1.dependencies import AdminUser, CurrentUser
from app.api.v1.responses import (
    BAD_REQUEST_RESPONSE,
    FORBIDDEN_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.api.v1.schemas.assets import AssetResponse
from app.api.v1.schemas.auth import (
    ChangePasswordRequest,
    UserListResponse,
    UserResponse,
)
from app.modules.asset.services import AssetService
from app.modules.auth.services import AuthService
from app.modules.user.services import UserService
from app.shared.schemas.common import (
    PaginatedSuccessResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

COOKIE_PATH = "/api/v1/auth"


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


@router.patch(
    "/me/password",
    status_code=status.HTTP_200_OK,
    description=(
        "Change the authenticated user's password. "
        "A successful password change invalidates all existing sessions, "
        "including the current session. The user must authenticate again "
        "using the new password."
    ),
    responses={
        **BAD_REQUEST_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def change_password(
    response: Response,
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DBSession,
) -> SuccessResponse[dict[str, str]]:
    service = AuthService(session)

    await service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
        path=COOKIE_PATH,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data={"message": "Password changed successfully"},
    )


@router.get(
    "/me/assets",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def get_my_assets(
    session: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, le=1000),
    size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> PaginatedSuccessResponse[list[AssetResponse]]:
    service = AssetService(session)

    assets, total = await service.list(
        page=page,
        size=size,
        assigned_to=current_user.id,
    )

    data = [
        AssetResponse.model_validate(asset).model_dump(mode="json") for asset in assets
    ]

    total_pages = ceil(total / size) if total else 0

    pagination = PaginationMeta(
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total,
    ).model_dump(mode="json")

    return success_response(
        status_code=status.HTTP_200_OK,
        data=data,
        pagination=pagination,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def list_users(
    session: DBSession,
    admin_user: AdminUser,
    page: int = Query(default=1, ge=1, le=1000),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
) -> PaginatedSuccessResponse[list[UserListResponse]]:
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

    pagination = PaginationMeta(
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total,
    ).model_dump(mode="json")

    return success_response(
        status_code=status.HTTP_200_OK,
        data=data,
        pagination=pagination,
    )
