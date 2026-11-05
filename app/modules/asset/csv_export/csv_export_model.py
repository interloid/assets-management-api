from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import BaseModel
from app.shared.models.mixins import CreatedAtMixin


class AssetExport(BaseModel, CreatedAtMixin):
    __tablename__ = "asset_exports"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_asset_exports_status",
        ),
    )

    requested_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )

    filters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
