from app.core.exceptions import AppError


class ExportNotFoundError(AppError):
    status_code = 404
    code = "EXPORT_NOT_FOUND"
    message = "The requested export was not found"


class ExportNotReadyError(AppError):
    status_code = 409
    code = "EXPORT_NOT_READY"
    message = "The export is not ready for download"


class ExportFileNotFoundError(AppError):
    status_code = 404
    code = "EXPORT_FILE_NOT_FOUND"
    message = "The export file could not be found"


class InvalidExportPathError(AppError):
    status_code = 500
    code = "INVALID_EXPORT_PATH"
    message = "The export file path is invalid"


class ExportQueueError(AppError):
    status_code = 503
    code = "EXPORT_QUEUE_UNAVAILABLE"
    message = "The export job could not be queued"
