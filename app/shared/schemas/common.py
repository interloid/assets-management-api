from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class APIModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PaginationMeta(APIModel):
    page: int
    size: int
    total_pages: int
    total_items: int


class SuccessResponse(APIModel, Generic[DataT]):
    data: DataT


class PaginatedSuccessResponse(SuccessResponse[DataT], Generic[DataT]):
    pagintion: PaginationMeta


class ErrorDetail(APIModel):
    field: str
    issue: str


class APIError(APIModel):
    code: str
    message: str


class ValidationAPIError(APIModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(APIModel):
    error: APIError


class ValidationErrorResponse(APIModel):
    error: ValidationAPIError
