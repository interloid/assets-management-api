from datetime import date
from math import ceil
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.constants.response import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.core.responses import success_response
from app.dependencies.types import AdminUser, CurrentUser, DBSession
from app.models.enums import AssetStatus, AssetType
from app.schemas.assets import (
    AssetAssign,
    AssetCreate,
    AssetResponse,
    AssetStatusUpdate,
    AssetUpdate,
)
from app.schemas.common import PaginationMeta, SuccessResponse
from app.services.assets import AssetService

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)


@router.post(
    "",
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
    "/summary",
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_asset_summary(
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
    "/my",
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
    page: int = Query(default=1, ge=1),
    size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> SuccessResponse[list[AssetResponse]]:
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
    "/{asset_id}",
    status_code=status.HTTP_200_OK,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def get_by_id(
    asset_id: UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.get_by_id(
        asset_id=asset_id,
        current_user=current_user,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.patch(
    "/{asset_id}",
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
    asset_id: UUID,
    data: AssetUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.update(
        asset_id=asset_id,
        data=data,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/{asset_id}",
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
    asset_id: UUID,
    _current_user: AdminUser,
    session: DBSession,
) -> None:
    service = AssetService(session)

    await service.delete(asset_id)


@router.post(
    "/{asset_id}/assign",
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
    asset_id: UUID,
    data: AssetAssign,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.assign(
        asset_id=asset_id,
        user_id=data.user_id,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.post(
    "/{asset_id}/unassign",
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
    asset_id: UUID,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.unassign(asset_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )


@router.post(
    "/{asset_id}/status",
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
    asset_id: UUID,
    data: AssetStatusUpdate,
    session: DBSession,
    _admin_user: AdminUser,
) -> SuccessResponse[AssetResponse]:
    service = AssetService(session)

    asset = await service.change_status(
        asset_id,
        data.status,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        data=AssetResponse.model_validate(
            asset,
        ).model_dump(mode="json"),
    )
