from fastapi import APIRouter, Query, status

from app.core.responses import success_response
from app.dependencies.types import AdminUser, DBSession
from app.schemas.auth import UserListData, UserListResponse
from app.schemas.common import SuccessEnvelope
from app.services.users import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def list_users(
    session: DBSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> SuccessEnvelope[UserListData]:
    service = UserService(session)

    users, total = await service.list_users(
        page=page,
        size=size,
        search=search,
    )

    data = UserListData(
        items=[UserListResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        size=size,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Users retrieved successfully",
        data=data.model_dump(mode="json"),
    )
