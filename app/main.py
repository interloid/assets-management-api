from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.core.lifespan import lifespan
from app.exceptions.base import AppError
from app.exceptions.handlers import (
    app_exception_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.routers import auth, health, root

app = FastAPI(
    title="Assets Management API",
    version="1.0.0",
    description="API for managing company assets and authentication",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(health.router)
app.include_router(root.router)
app.include_router(auth.router)
