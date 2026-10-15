from datetime import UTC, datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.shared.schemas.common import ErrorResponse


def app_error_handler(request: Request, exc: AppError):
    response =  ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
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
