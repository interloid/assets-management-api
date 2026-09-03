from app.exceptions.base import AppError


class AuthorizationError(AppError):
    status_code = 403
    code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"
