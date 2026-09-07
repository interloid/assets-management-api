from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "statusCode": exc.status_code,
            "message": exc.message,
            "data": None,
            "error": {
                "code": exc.code,
                "details": None,
            },
        },
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

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "statusCode": 422,
            "message": "Validation failed",
            "data": None,
            "error": {
                "code": "INVALID_INPUT",
                "details": errors,
            },
        },
    )


def unexpected_exception_handler(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "statusCode": 500,
            "message": "Internal server error",
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "details": None,
            },
        },
    )


def http_exception_handler(
    _request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "statusCode": 401,
                "message": "Authentication required",
                "data": None,
                "error": {
                    "code": "AUTHENTICATION_REQUIRED",
                    "details": "Authentication credentials were not provided",
                },
            },
            headers=exc.headers,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "statusCode": exc.status_code,
            "message": str(exc.detail),
            "data": None,
            "error": {
                "code": "HTTP_ERROR",
                "details": None,
            },
        },
        headers=exc.headers,
    )
