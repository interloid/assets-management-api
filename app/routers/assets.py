from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.responses import success_response
from app.dependencies.types import AdminUser, DBSession
from app.models.enums import AssetStatus, AssetType
from app.schemas.assets import AssetCreate, AssetResponse
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
