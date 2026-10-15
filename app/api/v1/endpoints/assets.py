from datetime import UTC, date, datetime
from math import ceil
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.deps import DBSession
from app.api.v1.dependencies import AdminUser, CurrentUser
from app.api.v1.responses import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.api.v1.schemas.assets import (
    AssetAssign,
    AssetCreate,
    AssetResponse,
    AssetStatsResponse,
    AssetStatusUpdate,
    AssetUpdate,
)
from app.modules.asset.services import AssetService
from app.shared.models.enums import AssetStatus, AssetType
from app.shared.schemas.common import (
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(
    prefix="/assets",
)

@router.post(
    "",
    tags=["Assets"],
    status_code=status.HTTP_201_CREATED,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def create_asset(
    request: Request,
    data: AssetCreate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.create(
        asset_type=data.type,
        serial_number=data.serial_number,
        purchase_date=data.purchase_date,
        warranty_expiry=data.warranty_expiry,
        notes=data.notes,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_201_CREATED,
        message="Asset created successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "",
    tags=["Assets"],
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def list_assets(
    request: Request,
    session: DBSession,
    _admin_user: AdminUser,
    page: int = Query(default=1, ge=1, le=1000),
    size: int = Query(default=20, ge=1, le=100),
    asset_type: AssetType | None = Query(default=None, alias="type"),
    asset_status: AssetStatus | None = Query(
        default=None,
        alias="status",
    ),
    assigned_to: UUID | None = None,
    warranty_expiring_before: date | None = None,
    search: str | None = None,
    sort: Literal["created_at", "purchase_date", "asset_tag"] = Query(
        default="created_at",
    ),
    order: Literal["asc", "desc"] = Query(default="desc"),
) -> SuccessResponse[list[AssetResponse]]:
    service = AssetService(session)

    assets, total = await service.list(
        page=page,
        size=size,
        asset_type=asset_type,
        asset_status=asset_status,
        assigned_to=assigned_to,
        warranty_expiring_before=warranty_expiring_before,
        search=search,
        sort=sort,
        order=order,
    )

    data = [
        AssetResponse.model_validate(asset) for asset in assets
    ]

    total_pages = ceil(total / size) if total else 0

    pagination = PaginationMeta(
        items_on_page=len(assets),
        page=page,
        records_per_page=size,
        total_items=total,
        total_pages=total_pages,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Assets retrieved successfully",
        data=data,
        pagination_meta=pagination,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

@router.get(
    "/stats",
    tags=["Assets"],
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_asset_stats(
    request: Request,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetStatsResponse]:
    service = AssetService(session)

    result = await service.stats()

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset statistics retrieved successfully",
        data=result,
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/{id}",
    tags=["Assets"],
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def get_by_id(
    request: Request,
    id: UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.get_by_id(
        asset_id=id,
        current_user=current_user,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset details retrieved successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.patch(
    "/{id}",
    tags=["Assets Update"],
    status_code=status.HTTP_200_OK,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def update_asset(
    request: Request,
    id: UUID,
    data: AssetUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    update_data = data.model_dump(exclude_unset=True)

    asset = await service.update(
        asset_id=id,
        update_data=update_data,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset updated successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.delete(
    "/{id}",
    tags=["Assets"],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def delete_asset(
    id: UUID,
    _current_user: AdminUser,
    session: DBSession,
) -> None:
    service = AssetService(session)

    await service.delete(id)

@router.post(
    "/{id}/assign",
    tags=["Asset Assignment"],
    status_code=status.HTTP_200_OK,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def assign_asset(
    request: Request,
    id: UUID,
    data: AssetAssign,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.assign(
        asset_id=id,
        user_id=data.user_id,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset assigned to user successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )



@router.post(
    "/{id}/unassign",
    tags=["Asset Assignment"],
    status_code=status.HTTP_200_OK,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def unassign_asset(
    request: Request,
    id: UUID,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.unassign(id)

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset unassigned from user successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )



@router.post(
    "/{id}/status",
    tags=["Assets Update"],
    status_code=status.HTTP_200_OK,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def change_status(
    request: Request,
    id: UUID,
    data: AssetStatusUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.change_status(
        id,
        data.status,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset status updated successfully",
        data=AssetResponse.model_validate(
            asset,
        ),
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )
