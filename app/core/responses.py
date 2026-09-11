from typing import Any

from fastapi.responses import JSONResponse


def success_response(
    *,
    status_code: int,
    message: str,
    data: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "statusCode": status_code,
            "message": message,
            "data": data,
            "error": None,
        },
    )


def error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "statusCode": status_code,
            "message": message,
            "data": None,
            "error": {
                "code": code,
                "details": details,
            },
        },
        headers=headers,
    )
