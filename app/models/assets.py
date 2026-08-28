from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.mixins import CreatedAtMixin, UpdatedAtMixin
from app.models.enums import AssetStatus, AssetType

if TYPE_CHECKING:
    from app.models.user import User


class Asset(
    BaseModel,
    CreatedAtMixin,
    UpdatedAtMixin,
):
    __tablename__ = "assets"

    asset_tag: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )

    type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )

    serial_number: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )

    status: Mapped[AssetStatus] = mapped_column(
        Enum(
            AssetStatus,
            name="asset_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=AssetStatus.IN_STOCK.value,
        index=True,
    )

    assigned_to: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    purchase_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    warranty_expiry: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assigned_user: Mapped["User | None"] = relationship(
        back_populates="assets",
    )

    __table_args__ = (
        CheckConstraint(
            "(status = 'assigned')= (assigned_to IS NOT NULL)",
            name="ck_assets_assignment_status",
        ),
    )
