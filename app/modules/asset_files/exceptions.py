from app.core.exceptions import AppError


class AssetFileNotFoundError(AppError):
    status_code = 404
    code = "ASSET_FILE_NOT_FOUND"
    message = "The asset file was not found"


class AssetFileForbiddenError(AppError):
    status_code = 403
    code = "ASSET_FILE_FORBIDDEN_ERROR"
    message = "Don't have permission to access this file"


class AssetFileValidationError(AppError):
    status_code = 422
    code = "ASSET_FILE_VALIDATION_ERROR"
    message = "Validation failed"
