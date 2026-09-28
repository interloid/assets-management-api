from sqlalchemy import CheckConstraint, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base
from app.shared.models.enums import AssetType


class AssetTagCounter(Base):
    __tablename__ = "asset_tag_counters"

    __table_args__ = (
        CheckConstraint(
            "last_number >= 0",
            name="ck_asset_tag_counters_last_number_non_negative",
        ),
    )

    company_prefix: Mapped[str] = mapped_column(String(20), primary_key=True)

    asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            values_callable=lambda enum: [member.value for member in enum],
            create_type=False,
        ),
        primary_key=True,
    )

    last_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
