from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.exception_handlers import (
    app_error_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.api.health.router import router as health_router
from app.api.router import router as api_router
from app.core.exceptions import AppError
from app.infrastructure.lifespan import lifespan

app = FastAPI(
    title="Assets Management API",
    version="1.0.0",
    description="API for managing company assets and authentication",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)
app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.include_router(health_router)
app.include_router(api_router)
