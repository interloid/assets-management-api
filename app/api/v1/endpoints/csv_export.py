from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request, status
from fastapi.responses import FileResponse

from app.api.deps import DBSession
from app.api.v1.dependencies import AdminUser
from app.api.v1.responses import (
    FORBIDDEN_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.api.v1.schemas.assets import AssetExportRequest
from app.modules.asset.csv_export.csv_export_service import AssetExportService
from app.shared.schemas.common import SuccessResponse

router = APIRouter(
    prefix="/assets",
)


@router.post(
    "/export",
    tags=["Asset Export"],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def create_asset_export(
    request: Request,
    filters: AssetExportRequest,
    session: DBSession,
    admin_user: AdminUser,
) -> SuccessResponse[dict]:
    service = AssetExportService(session)

    export = await service.create_export(
        requested_by=admin_user.id,
        filters=filters.model_dump(
            exclude_none=True,
            mode="json",
        ),
    )

    data = {
        "export_id": str(export.id),
        "status": export.status,
    }

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_202_ACCEPTED,
        message="Asset export queued successfully",
        data=data,
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/export/{export_id}",
    tags=["Asset Export"],
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_asset_export_status(
    request: Request,
    export_id: UUID,
    session: DBSession,
    admin_user: AdminUser,
) -> SuccessResponse[dict]:
    service = AssetExportService(session)

    export = await service.get_export(export_id)

    data = {
        "export_id": str(export.id),
        "status": export.status,
        "created_at": export.created_at,
        "download_url": (
            f"api/v1/assets/export/{export.id}/download"
            if export.status == "completed" and export.file_path
            else None
        ),
    }

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset export status retrieved successfully",
        data=data,
        pagination_meta=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/export/{export_id}/download",
    tags=["Asset Export"],
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
    },
)
async def download_asset_export(
    export_id: UUID,
    session: DBSession,
    _admin_user: AdminUser,
) -> FileResponse:
    service = AssetExportService(session)
    file_path = await service.get_download_path(export_id)

    return FileResponse(
        path=file_path, media_type="text/csv", filename=f"assets-{export_id}.csv"
    )
