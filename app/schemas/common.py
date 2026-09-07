from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ErrorDetail(APIModel):
    code: str
    details: Any


class ValidationErrorDetail(APIModel):
    field: str
    message: str


class APIError(APIModel):
    code: str
    details: str | list[ValidationErrorDetail]


class SuccessResponse(APIModel):
    success: bool = True
    status_code: int = Field(alias="statusCode")
    message: str
    data: Any | None = None
    error: None = None


class ErrorResponse(APIModel):
    success: bool = False
    status_code: int = Field(alias="statusCode")
    message: str
    data: None
    error: APIError
