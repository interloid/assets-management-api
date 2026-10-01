from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.responses import error_response
from app.core.exceptions import AppError


def app_error_handler(_request: Request, exc: AppError):
    return error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        details=exc.details,
        headers=exc.headers,
    )


def validation_exception_handler(
    _request: Request,
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
                "issue": issue,
            }
        )

    return error_response(
        status_code=422,
        message="Request validation failed",
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
            message="Authentication credentials are required",
            code="AUTHENTICATION_REQUIRED",
            headers=exc.headers,
        )
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        code="HTTP_ERROR",
        headers=exc.headers,
    )
