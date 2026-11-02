"""add asset tag counters

Revision ID: 1feee324eade
Revises: 5df3f4373520
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1feee324eade"
down_revision: Union[str, Sequence[str], None] = "5df3f4373520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    asset_type_enum = postgresql.ENUM(
        "laptop",
        "monitor",
        "phone",
        "accessory",
        name="asset_type",
        create_type=False,
    )

    op.create_table(
        "asset_tag_counters",
        sa.Column(
            "company_prefix",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "asset_type",
            asset_type_enum,
            nullable=False,
        ),
        sa.Column(
            "last_number",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "company_prefix",
            "asset_type",
        ),
        sa.CheckConstraint(
            "last_number >= 0",
            name="ck_asset_tag_counters_last_number_non_negative",
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_tag_counters")
