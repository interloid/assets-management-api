# api/v1/system.py
from fastapi import APIRouter, status

from app.core.responses import success_response
from app.dependencies.redis import RedisClient
from app.dependencies.types import DBSession
from app.exceptions.base import ServiceUnavailableError
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.system import HealthResponse, HomeResponse
from app.services.health import check_dependencies

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
        raise ServiceUnavailableError()
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
