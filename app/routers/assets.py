from fastapi import APIRouter, status

from app.core.responses import success_response
from app.dependencies.types import AdminUser, DBSession
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
