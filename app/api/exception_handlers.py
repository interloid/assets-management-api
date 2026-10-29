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


def app_error_handler(request: Request, exc: AppError):
    response = ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
        errors=exc.errors,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
        headers=exc.headers,
    )


def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
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

    response = ErrorResponse(
        success=False,
        status_code=422,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        errors=details,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(mode="json"),
    )


def unexpected_exception_handler(request: Request, _exc: Exception):

    response = ErrorResponse(
        success=False,
        status_code=500,
        message="Internal server error",
        error_code="INTERNAL_ERROR",
        errors=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content=response.model_dump(mode="json"),
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        message = "Authentication credentials are required"
        code = "AUTHENTICATION_REQUIRED"
    else:
        message = str(exc.detail)
        code = "HTTP_ERROR"

    response = ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=code,
        message=message,
        errors=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
        headers=exc.headers,
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

    response = ErrorResponse(
        success=False,
        status_code=429,
        message=(f"Rate limit exceeded. Please retry after {retry_after} seconds."),
        error_code="RATE_LIMIT_EXCEEDED",
        errors=None,
        request_id=None,
        timestamp=datetime.now(UTC),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=429,
        content=response.model_dump(mode="json"),
        headers={"Retry-After": str(retry_after)},
    )
