from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.responses import error_response
from app.exceptions.base import AppError

SENSITIVE_FIELDS = {
    "password",
    "current_password",
    "new_password",
    "refresh_token",
    "access_token",
}


def app_exception_handler(
    _request: Request,
    exc: AppError,
) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        headers=exc.headers,
    )


def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = []

    for error in exc.errors():
        error = error.copy()

        loc = error.get("loc", [])

        if any(field in SENSITIVE_FIELDS for field in loc):
            error.pop("input", None)

        error.pop("ctx", None)

        errors.append(error)

    return error_response(
        status_code=422,
        message="Validation failed",
        code="INVALID_INPUT",
        details=errors,
    )


def unexpected_exception_handler(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return error_response(
        status_code=500,
        message="Internal server error",
        code="INTERNAL_ERROR",
    )


def http_exception_handler(
    _request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if exc.status_code == 401:
        return error_response(
            status_code=401,
            message="Authentication required",
            code="AUTHENTICATION_REQUIRED",
            details="Authentication credentials were not provided",
            headers=exc.headers,
        )

    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        code="HTTP_ERROR",
        headers=exc.headers,
    )
