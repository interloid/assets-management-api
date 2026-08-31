from app.exceptions.base import AppError


class EmailAlreadyRegisteredError(AppError):
    pass


class InvalidCredentialsError(AppError):
    pass
