from typing import Any

from fastapi.responses import JSONResponse


def success_response(
    *,
    status_code: int,
    data: Any = None,
    pagination: dict[str, Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "data": data,
    }

    if pagination is not None:
        content["pagination"] = pagination

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


def error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
        },
        headers=headers,
    )
