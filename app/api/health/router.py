from datetime import UTC, datetime

from fastapi import APIRouter, Request, status

from app.api.deps import DBSession, RedisClient
from app.api.health.schemas import HealthResponse, HomeResponse
from app.api.health.service import check_dependencies
from app.core.exceptions import ServiceUnavailableError
from app.shared.schemas.common import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse[HealthResponse],
    response_model_exclude_none=True,
    responses={503: {"model": ErrorResponse}},
)
async def health_check(request: Request, session: DBSession, redis_client: RedisClient):
    services = await check_dependencies(session, redis_client)

    if not all(s.status == "ok" for s in services.values()):
        raise ServiceUnavailableError(
            message="One or more required services are unavailable",
            errors=[
                {
                    "field": "services",
                    "message": "Health check detected degraded dependencies",
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
        message="Health check completed successfully",
        data=HealthResponse(
            status="ok",
            services=services,
        ),
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
async def home(request: Request) -> SuccessResponse[HomeResponse]:
    return SuccessResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message="Welcome to the Assets Management API",
        data=HomeResponse(
            name="Assets Management API",
            version="1.0.0",
        ),
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )
