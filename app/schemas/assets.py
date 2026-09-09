from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.assets import AssetStatus, AssetType
from app.validators.serial_number import validate_serial_number


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AssetType
    serial_number: str
    purchase_date: date
    warranty_expiry: date | None = None
    notes: str | None = None

    _validate_serial_number = field_validator(
        "serial_number",
    )(validate_serial_number)


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_tag: str
    type: AssetType
    serial_number: str
    status: AssetStatus
    assigned_to: UUID | None
    purchase_date: date
    warranty_expiry: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    page: int
    size: int
    total: int
    pages: int
