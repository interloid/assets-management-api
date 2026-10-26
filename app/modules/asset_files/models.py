from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.asset.models import Asset
from app.shared.models.base import BaseModel
from app.shared.models.enums import FileType, FileUploadStatus
from app.shared.models.mixins import CreatedAtMixin, UpdatedAtMixin


class AssetFiles(
    BaseModel,
    CreatedAtMixin,
    UpdatedAtMixin,
):
    __tablename__ = "asset_files"

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[FileType] = mapped_column(
        Enum(
            FileType,
            name="file_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    s3_object_key: Mapped[str] = mapped_column(
        String(1024), unique=True, nullable=False
    )

    status: Mapped[FileUploadStatus] = mapped_column(
        Enum(
            FileUploadStatus,
            name="file_upload_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=FileUploadStatus.PENDING,
    )

    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="asset_files")
