import logging
import math
import time
from datetime import UTC, datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.shared.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def request_log_context(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "user_id": getattr(request.state, "user_id", None),
        "method": request.method,
        "path": request.url.path,
    }


def app_error_handler(request: Request, exc: AppError):
    context = request_log_context(request)

    log_context = {
        **context,
        "status_code": exc.status_code,
    }

    if exc.status_code >= 500:
        logger.error(
            "Application error: %s",
            exc.code,
            extra=log_context,
        )
    else:
        logger.warning(
            "Application error: %s",
            exc.code,
            extra=log_context,
        )

    headers = dict(exc.headers or {})
    request_id = getattr(request.state, "request_id", None)

    if request_id:
        headers["X-Request-ID"] = request_id

    response = ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
        errors=exc.errors,
        request_id=request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
        headers=headers,
    )


def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    logger.warning(
        "Request validation failed",
        extra={
            **request_log_context(request),
            "status_code": 422,
        },
    )

    details = []

    for error in exc.errors():
        loc = error.get("loc", [])

        fields = [
            str(field)
            for field in loc
            if field not in {"body", "query", "path"} and not isinstance(field, int)
        ]

        field = ".".join(fields) if fields else "request"
        issue = error.get("msg", "Invalid value")

        if issue.startswith("Value error, "):
            issue = issue.removeprefix("Value error, ")

        details.append(
            {
                "field": field,
                "message": issue,
            }
        )

    request_id = getattr(request.state, "request_id", None)

    response = ErrorResponse(
        success=False,
        status_code=422,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        errors=details,
        request_id=request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    headers = {"X-Request-ID": request_id} if request_id else {}

    return JSONResponse(
        status_code=422,
        content=response.model_dump(mode="json"),
        headers=headers,
    )


def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Unhandled server exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            **request_log_context(request),
            "status_code": 500,
        },
    )

    response = ErrorResponse(
        success=False,
        status_code=500,
        message="Internal server error",
        error_code="INTERNAL_ERROR",
        errors=None,
        request_id=request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    headers = {"X-Request-ID": request_id} if request_id else {}

    return JSONResponse(
        status_code=500,
        content=response.model_dump(mode="json"),
        headers=headers,
    )


def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    log_context = {
        **request_log_context(request),
        "status_code": exc.status_code,
    }

    if exc.status_code >= 500:
        logger.error(
            "HTTP exception",
            extra=log_context,
        )
    else:
        logger.warning(
            "HTTP exception",
            extra=log_context,
        )

    if exc.status_code == 401:
        message = "Authentication credentials are required"
        code = "AUTHENTICATION_REQUIRED"
    else:
        message = str(exc.detail)
        code = "HTTP_ERROR"

    headers = dict(exc.headers or {})
    request_id = getattr(request.state, "request_id", None)

    if request_id:
        headers["X-Request-ID"] = request_id

    response = ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=code,
        message=message,
        errors=None,
        request_id=request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
        headers=headers,
    )


def rate_limit_exception_handler(
    request: Request,
    _exc: RateLimitExceeded,
) -> JSONResponse:
    retry_after = 60

    try:
        current_limit = request.state.view_rate_limit

        if current_limit is not None:
            rate_limit_item, identifiers = current_limit

            limiter = request.app.state.limiter
            window_stats = limiter.limiter.get_window_stats(
                rate_limit_item,
                *identifiers,
            )

            retry_after = max(
                1,
                math.ceil(window_stats.reset_time - time.time()),
            )
    except (AttributeError, TypeError, ValueError):
        pass

    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "Rate limit exceeded",
        extra={
            **request_log_context(request),
            "status_code": 429,
        },
    )

    headers = {"Retry-After": str(retry_after)}

    if request_id:
        headers["X-Request-ID"] = request_id

    response = ErrorResponse(
        success=False,
        status_code=429,
        message=(f"Rate limit exceeded. Please retry after {retry_after} seconds."),
        error_code="RATE_LIMIT_EXCEEDED",
        errors=None,
        request_id=request_id,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=429,
        content=response.model_dump(mode="json"),
        headers=headers,
    )
