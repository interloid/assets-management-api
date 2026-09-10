from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.responses import success_response
from app.dependencies.types import AdminUser, CurrentUser, DBSession
from app.models.enums import AssetStatus, AssetType
from app.schemas.assets import AssetAssign, AssetCreate, AssetResponse, AssetUpdate
from app.services.assets import AssetService

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    session: DBSession,
    _admin_user: AdminUser,
) -> AssetResponse:
    service = AssetService(session)

    asset = await service.create(data)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Asset created successfully",
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.get("")
async def list_assets(
    session: DBSession,
    _admin_user: AdminUser,
    page: int = Query(
        default=1,
        ge=1,
    ),
    size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    asset_type: AssetType | None = Query(default=None, alias="type"),
    asset_status: AssetStatus | None = None,
    assigned_to: UUID | None = None,
    warranty_expiring_before: date | None = None,
    search: str | None = None,
    sort: Literal["created_at"] = Query(default="created_at"),
):
    service = AssetService(session)

    result = await service.list(
        page=page,
        size=size,
        asset_type=asset_type,
        asset_status=asset_status,
        assigned_to=assigned_to,
        warranty_expiring_before=warranty_expiring_before,
        search=search,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Assets retrieved successfully",
        data=result.model_dump(mode="json"),
    )


@router.get("/my", status_code=status.HTTP_200_OK)
async def get_my_assets(
    session: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    service = AssetService(session)

    result = await service.list(page=page, size=size, assigned_to=current_user.id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Assets retrived successfully",
        data=result.model_dump(mode="json"),
    )


@router.get("/{asset_id}", status_code=status.HTTP_200_OK)
async def get_by_id(
    asset_id: UUID, session: DBSession, current_user: CurrentUser
) -> AssetResponse:
    service = AssetService(session)

    asset = await service.get_by_id(
        asset_id=asset_id,
        current_user=current_user,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Asset retrieved successfully",
        data=AssetResponse.model_validate(asset).model_dump(mode="json"),
    )


@router.patch("/{asset_id}", status_code=status.HTTP_200_OK)
async def update_asset(
    asset_id: UUID,
    data: AssetUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> AssetResponse:
    service = AssetService(session)

    asset = await service.update(
        asset_id=asset_id,
        data=data,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Asset updated successfully",
        data=AssetResponse.model_validate(asset).model_dump(mode="json"),
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    _current_user: AdminUser,
    session: DBSession,
) -> None:
    service = AssetService(session)

    await service.delete(asset_id)

    return None


@router.post(
    "/{asset_id}/assign",
    status_code=status.HTTP_200_OK,
)
async def assign_asset(
    asset_id: UUID,
    data: AssetAssign,
    session: DBSession,
    _admin_user: AdminUser,
) -> AssetResponse:
    service = AssetService(session)

    asset = await service.assign(
        asset_id=asset_id,
        user_id=data.user_id,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Asset assigned successfully",
        data=AssetResponse.model_validate(asset).model_dump(mode="json"),
    )


@router.post(
    "/{asset_id}/unassign",
    status_code=status.HTTP_200_OK,
)
async def unassign_asset(
    asset_id: UUID,
    session: DBSession,
    _admin_user: AdminUser,
) -> AssetResponse:
    service = AssetService(session)

    asset = await service.unassign(asset_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Asset unassigned successfully",
        data=AssetResponse.model_validate(asset).model_dump(mode="json"),
    )
