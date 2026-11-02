from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class APIModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PaginationMeta(APIModel):
    items_on_page: int
    page: int
    records_per_page: int
    total_items: int
    total_pages: int


class SuccessResponse(APIModel, Generic[DataT]):
    success: bool = True
    status_code: int
    message: str
    data: DataT
    pagination_meta: PaginationMeta | None = None
    request_id: UUID | None = None
    timestamp: datetime
    path: str


class PaginatedSuccessResponse(SuccessResponse[DataT]):
    pagination_meta: PaginationMeta


class ErrorDetail(APIModel):
    field: str
    message: str


class ErrorResponse(APIModel):
    success: bool = False
    status_code: int
    error_code: str
    message: str
    errors: list[ErrorDetail] | None = None
    request_id: UUID | None = None
    timestamp: datetime
    path: str
