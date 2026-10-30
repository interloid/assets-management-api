from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, Text, true
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import BaseModel
from app.shared.models.enums import UserRole
from app.shared.models.mixins import CreatedAtMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from app.modules.asset.asset_assignment import AssetAssignment
    from app.modules.asset.models import Asset
    from app.modules.asset.tag.asset_tag_history import AssetTagHistory
    from app.modules.auth.models import RefreshToken


class User(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        CITEXT(),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=UserRole.USER.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    asset_assignments: Mapped[list["AssetAssignment"]] = relationship(
        "AssetAssignment",
        foreign_keys="AssetAssignment.user_id",
        back_populates="user",
    )

    created_asset_assignments: Mapped[list["AssetAssignment"]] = relationship(
        "AssetAssignment",
        foreign_keys="AssetAssignment.assigned_by",
        back_populates="assigner",
    )

    unassigned_asset: Mapped[list["AssetAssignment"]] = relationship(
        "AssetAssignment",
        foreign_keys="AssetAssignment.unassigned_by",
        back_populates="un_assigner",
    )

    asset_tag_changes: Mapped[list["AssetTagHistory"]] = relationship(
        "AssetTagHistory",
        foreign_keys="AssetTagHistory.changed_by",
        back_populates="changed_by_user",
    )

    assets: Mapped[list["Asset"]] = relationship(back_populates="assigned_user")
