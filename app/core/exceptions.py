from typing import Any


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
    headers: dict[str, str] | None = None
    details: Any = None

    def __init__(
        self,
        message: str | None = None,
        headers: dict[str, str] | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.headers = headers or self.headers
        self.details = details
        super().__init__(self.message)


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "One or more required services are unavailable"
