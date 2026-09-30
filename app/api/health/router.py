# api/v1/system.py
from fastapi import APIRouter, status

from app.api.deps import DBSession, RedisClient
from app.api.health.schemas import HealthResponse, HomeResponse
from app.api.health.service import check_dependencies
from app.api.responses import success_response
from app.core.exceptions import ServiceUnavailableError
from app.shared.schemas.common import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse[HealthResponse],
    response_model_exclude_none=True,
    responses={503: {"model": ErrorResponse}},
)
async def health_check(session: DBSession, redis_client: RedisClient):
    services = await check_dependencies(session, redis_client)
    if not all(s.status == "ok" for s in services.values()):
        raise ServiceUnavailableError(
            details={
                "status": "degraded",
                "services": services,
            }
        )
    return SuccessResponse(data=HealthResponse(status="ok", services=services))


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
async def home() -> SuccessResponse[HomeResponse]:
    return success_response(
        status_code=status.HTTP_200_OK,
        data=HomeResponse(
            name="Asset Management API",
            version="1.0.0",
        ).model_dump(mode="json"),
    )
