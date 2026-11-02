from app.core.exceptions import AppError


class InvalidCurrentPasswordError(AppError):
    status_code = 400
    code = "INVALID_CURRENT_PASSWORD"
    message = "Current password is incorrect"
