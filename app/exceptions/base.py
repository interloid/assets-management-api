class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
    headers: dict[str, str] | None = None

    def __init__(
        self,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.headers = headers

        super().__init__(self.message)
