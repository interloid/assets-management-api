import hmac
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DBSession
from app.api.v1.responses import (
    BAD_REQUEST_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_RESPONSE,
)
from app.core.config import settings
from app.modules.asset_files.service import AssetFileService
from app.shared.schemas.common import SuccessResponse

router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
)


class S3UploadCompletedRequest(BaseModel):
    bucket: str = Field(min_length=1)
    object_key: str = Field(min_length=1)
    event_size: int = Field(ge=0)


@router.post(
    "/s3-upload-completed",
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **BAD_REQUEST_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
        **VALIDATION_RESPONSE,
    },
)
async def s3_upload_completed(
    request: Request,
    data: S3UploadCompletedRequest,
    session: DBSession,
    x_s3_upload_secret: str = Header(alias="X-S3-Upload-Secret"),
) -> SuccessResponse[dict]:
    if not hmac.compare_digest(
        x_s3_upload_secret,
        settings.S3_UPLOAD_CALLBACK_SECRET,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid callback secret",
        )

    if data.bucket != settings.S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected S3 bucket",
        )

    service = AssetFileService(session)

    file = await service.process_s3_upload_event(
        object_key=data.object_key,
    )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="S3 upload event processed successfully",
        data={
            "file_id": str(file.id),
            "status": file.status.value,
        },
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )
