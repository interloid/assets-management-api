from fastapi import FastAPI

from app.exceptions.base import AppError
from app.exceptions.handlers import (
    app_exception_handler,
    unexpected_exception_handler,
)
from app.routers import auth

app = FastAPI(
    title="Assets Management API",
    version="1.0.0",
    description="API for managing company assets and authentication",
)

app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)

app.include_router(auth.router)


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "This is Assets Management System"}
