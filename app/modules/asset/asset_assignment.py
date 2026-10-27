from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.asset.models import Asset
    from app.modules.user.models import User


class AssetAssignment(BaseModel):
    __tablename__ = "asset_assignments"

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    unassigned_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="assignments",
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="asset_assignments",
    )

    assigner: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by],
        back_populates="created_asset_assignments",
    )

    un_assigner: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[unassigned_by],
        back_populates="unassigned_asset",
    )

    __table_args__ = (
        Index(
            "uq_asset_assignments_open_asset",
            "asset_id",
            unique=True,
            postgresql_where=(returned_at.is_(None)),
        ),
        Index(
            "ix_asset_assignments_asset_assigned_at",
            "asset_id",
            "assigned_at",
        ),
        Index(
            "ix_asset_assignments_user_assigned_at",
            "user_id",
            "assigned_at",
        ),
    )
