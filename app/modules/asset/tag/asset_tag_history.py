from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import BaseModel
from app.shared.models.enums import AssetType

if TYPE_CHECKING:
    from app.modules.asset.models import Asset
    from app.modules.user.models import User


class AssetTagHistory(BaseModel):
    __tablename__ = "asset_tag_history"

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
    )

    old_asset_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    old_asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    new_asset_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    new_asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    changed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="tag_history",
    )

    changed_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[changed_by],
        back_populates="asset_tag_changes",
    )

    __table_args__ = (
        Index(
            "ix_asset_tag_history_asset_changed_at",
            "asset_id",
            "changed_at",
        ),
    )
