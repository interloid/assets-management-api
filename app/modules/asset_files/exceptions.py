from app.core.exceptions import AppError


class AssetFileNotFoundError(AppError):
    status_code = 404
    code = "ASSET FILE NOT FOUND"
    message = "The aset file was not found"


class AssetFileForbiddenError(AppError):
    status_code = 403
    code = "ASSET FILE FORBIDDEN ERROR"
    message = "Dont have permission to access this file"


class AssetFileValidationError(AppError):
    status_code = 422
    code = "ASSET FILE VALIDATION ERROR"
    message = "Validation failed"
