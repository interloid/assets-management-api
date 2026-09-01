from fastapi import FastAPI

from app.exceptions.base import AppError
from app.exceptions.handlers import app_exception_handler, unexpected_exception_handler
from app.routers import auth

app = FastAPI()

app.include_router(auth.router)


@app.get("/")
def home():
    return {"message": "This is Assets Management System"}


app.add_exception_handler(
    AppError,
    app_exception_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_exception_handler,
)
