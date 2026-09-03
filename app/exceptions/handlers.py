import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.base import AppError

logger = logging.getLogger(__name__)


def app_exception_handler(
    _request: Request,
    exc: AppError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=exc.headers,
    )


def unexpected_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
