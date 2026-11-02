# from typing import Any

# from fastapi.responses import JSONResponse


# def success_response(
#     request: Request,
#     *,
#     status_code: int,
#     message: str,
#     data: Any = None,
#     pagination_meta: dict[str, Any] | None = None,
# ) -> JSONResponse:
#     content: dict[str, Any] = {
#         "success": True,
#         "status_code": status_code,
#         "message": message,
#         "data": data,
#         "pagination_meta": pagination_meta,
#         "request_id": None,
#         "timestamp":
#     }

#     return JSONResponse(
#         status_code=status_code,
#         content=jsonable_encoder(content),
#     )


# def error_response(
#     *,
#     status_code: int,
#     message: str,
#     code: str,
#     details: Any = None,
#     headers: dict[str, str] | None = None,
# ) -> JSONResponse:
#     error: dict[str, Any] = {
#         "code": code,
#         "message": message,
#     }

#     if details is not None:
#         error["details"] = details

#     return JSONResponse(
#         status_code=status_code,
#         content={
#             "error": error,
#         },
#         headers=headers,
#     )


