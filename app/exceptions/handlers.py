from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response
from app.exceptions.base import AppError


def app_error_handler(_request: Request, exc: AppError):
    return error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        headers=exc.headers,
    )


def validation_exception_handler(_request: Request, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        loc = error.get("loc", [])
        fields = [str(f) for f in loc if f not in {"body", "query", "path"}]
        details.append(
            {
                "field": ".".join(fields) if fields else "request",
                "issue": error.get("msg", "Invalid value"),
            }
        )
    return error_response(
        status_code=422,
        message="Invalid input",
        code="VALIDATION_ERROR",
        details=details,
    )


def unexpected_exception_handler(_request: Request, _exc: Exception):
    return error_response(
        status_code=500, message="Internal server error", code="INTERNAL_ERROR"
    )


def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return error_response(
            status_code=401,
            message="Authentication credentials were not provided",
            code="AUTHENTICATION_REQUIRED",
            headers=exc.headers,
        )
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        code="HTTP_ERROR",
        headers=exc.headers,
    )
