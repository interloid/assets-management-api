from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request, status

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
    AssetFileConfirmResponse,
    AssetFileResponse,
    AssetFileUploadRequest,
    AssetFileUploadResponse,
)
from app.modules.asset_files.service import AssetFileService
from app.shared.schemas.common import SuccessResponse

router = APIRouter(
    prefix="/assets",
    tags=["Asset Files"],
)


@router.post(
    "/{id}/files/presign",
    status_code=status.HTTP_201_CREATED,
    responses={
        **CONFLICT_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def generate_upload_url(
    request: Request,
    id: UUID,
    data: AssetFileUploadRequest,
    session: DBSession,
    current_user: AdminUser,
) -> SuccessResponse[AssetFileUploadResponse]:
    service = AssetFileService(session)

    file = await service.create_upload(
        asset_id=id,
        filename=data.filename,
        content_type=data.content_type,
        file_size=data.file_size,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_201_CREATED,
        message="Upload URL generated successfully",
        data=AssetFileUploadResponse.model_validate(file),
        request_id=request.state.request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.post(
    "/{id}/files/{file_id}/confirm",
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
async def confirm_upload(
    request: Request, id: UUID, file_id: UUID, session: DBSession, admin_user: AdminUser
) -> SuccessResponse[AssetFileConfirmResponse]:

    service = AssetFileService(session)

    file = await service.confirm_upload(asset_id=id, file_id=file_id)

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="File upload confirmed successfully",
        data=AssetFileConfirmResponse.model_validate(file),
        request_id=request.state.request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/{id}/files",
    status_code=status.HTTP_200_OK,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def get_files(
    request: Request,
    id: UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> SuccessResponse[list[AssetFileResponse]]:
    service = AssetFileService(session)

    files = await service.list_files(
        asset_id=id,
        current_user=current_user,
    )

    data = [AssetFileResponse.model_validate(file) for file in files]

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Asset files retrieved successfully",
        data=data,
        request_id=request.state.request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.delete(
    "/{id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **FORBIDDEN_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def delete_file(
    id: UUID,
    file_id: UUID,
    session: DBSession,
    admin_user: AdminUser,
) -> None:
    service = AssetFileService(session)

    await service.delete_file(asset_id=id, file_id=file_id)
