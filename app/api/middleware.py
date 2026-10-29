import logging
import time
from uuid import UUID, uuid4

from fastapi import Request

logger = logging.getLogger(__name__)


def resolve_request_id(value: str | None) -> str:
    if value:
        try:
            return str(UUID(value))
        except (ValueError, TypeError, AttributeError):
            pass

    return str(uuid4())


async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = resolve_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id

    started_at = time.perf_counter()

    log_context = {
        "request_id": request_id,
        "user_id": getattr(request.state, "user_id", None),
        "method": request.method,
        "path": request.url.path,
    }

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            "HTTP request failed",
            extra={
                **log_context,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    response.headers["X-Request-ID"] = request_id

    log_context.update(
        {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )

    logger.info(
        "HTTP request completed",
        extra=log_context,
    )

    return response
