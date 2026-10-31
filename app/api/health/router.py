from datetime import UTC, datetime

from fastapi import APIRouter, Request, status

from app.api.deps import DBSession, RedisClient
from app.api.health.schemas import (
    HealthResponse,
    LivenessResponse,
)
from app.api.health.service import check_dependencies
from app.api.v1.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
)
from app.core.exceptions import ServiceUnavailableError
from app.shared.schemas.common import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse[LivenessResponse],
    response_model_exclude_none=True,
    responses={
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def health_check(request: Request):
    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Application is alive",
        data=LivenessResponse(
            status="ok",
            version=request.app.version,
        ),
        request_id=request.state.request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/health/ready",
    response_model=SuccessResponse[HealthResponse],
    response_model_exclude_none=True,
    responses={503: {"model": ErrorResponse}},
)
async def readiness_check(
    request: Request,
    session: DBSession,
    redis_client: RedisClient,
):
    services = await check_dependencies(session, redis_client)

    if not all(service.status == "ok" for service in services.values()):
        raise ServiceUnavailableError(
            message="One or more required services are unavailable",
            errors=[
                {
                    "field": "services",
                    "message": "Readiness check detected unavailable dependencies",
                    "details": {
                        "status": "degraded",
                        "services": {
                            key: value.model_dump() for key, value in services.items()
                        },
                    },
                }
            ],
        )

    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Application is ready",
        data=HealthResponse(
            status="ok",
            services=services,
        ),
        request_id=request.state.request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )
