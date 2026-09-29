from datetime import date
from math import ceil
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

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
    AssetStatusUpdate,
    AssetUpdate,
)
from app.core.responses import success_response
from app.modules.asset.services import AssetService
from app.shared.models.enums import AssetStatus, AssetType
from app.shared.schemas.common import (
    PaginatedSuccessResponse,
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
    data: AssetCreate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.create(data)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
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
    session: DBSession,
    _admin_user: AdminUser,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    asset_type: AssetType | None = Query(default=None, alias="type"),
    asset_status: AssetStatus | None = None,
    assigned_to: UUID | None = None,
    warranty_expiring_before: date | None = None,
    search: str | None = None,
    sort: Literal["created_at", "purchase_date", "asset_tag"] = Query(
        default="created_at",
    ),
    order: Literal["asc", "desc"] = Query(default="desc"),
) -> PaginatedSuccessResponse[list[AssetResponse]]:
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
        AssetResponse.model_validate(asset).model_dump(mode="json") for asset in assets
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
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[dict[str, int]]:
    service = AssetService(session)

    result = await service.summary()

    return success_response(
        status_code=status.HTTP_200_OK,
        data=result,
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
    id: UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.get_by_id(
        asset_id=id,
        current_user=current_user,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.patch(
    "/{id}",
    tags=["Assets Update"],
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def update_asset(
    id: UUID,
    data: AssetUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.update(
        asset_id=id,
        data=data,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
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
    tags=["Asset Assign/Un-Assign"],
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

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.post(
    "/{id}/unassign",
    tags=["Asset Assign/Un-Assign"],
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
    id: UUID,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.unassign(id)

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
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

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )
