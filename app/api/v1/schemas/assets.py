from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.modules.asset.validators.serial_number import validate_serial_number
from app.shared.models.enums import AssetStatus, AssetType


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


class AssignedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    email: str


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_tag: str
    type: AssetType
    serial_number: str
    status: AssetStatus
    assigned_user: AssignedUserResponse | None = Field(
        default=None,
        validation_alias="assigned_user",
    )
    purchase_date: date
    warranty_expiry: date | None

    @computed_field
    @property
    def warranty_expires_in_days(self) -> str:
        if not self.warranty_expiry:
            return "No Warranty"

        delta = (self.warranty_expiry - date.today()).days

        if delta <= -1:
            return "Expired"
        elif delta == 0:
            return "Expires Today"
        else:
            return str(delta)

    notes: str | None
    created_at: datetime
    updated_at: datetime


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AssetType | None = None
    notes: str | None = None
    purchase_date: date | None = None
    warranty_expiry: date | None = None
    serial_number: str | None = None

    @field_validator("type", "purchase_date", "serial_number", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("serial_number")
    @classmethod
    def validate_serial_number_field(cls, value: str) -> str:
        return validate_serial_number(value)


class AssetAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class AssetStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AssetStatus


class AssetStatsResponse(BaseModel):
    total: int
    in_stock: int
    assigned: int
    repair: int
    retired: int
