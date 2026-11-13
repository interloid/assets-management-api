"""allow checksum reuse after asset file deletion

Revision ID: f14a607db358
Revises: 51c263f021bf
Create Date: 2026-11-12 12:20:36.520196
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f14a607db358"
down_revision: Union[str, Sequence[str], None] = "51c263f021bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow checksum reuse after soft deletion."""

    op.drop_constraint(
        "uq_asset_files_asset_id_checksum_sha256",
        "asset_files",
        type_="unique",
    )

    op.create_index(
        "uq_asset_files_asset_id_checksum_sha256",
        "asset_files",
        ["asset_id", "checksum_sha256"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )


def downgrade() -> None:
    """Restore the original checksum uniqueness constraint."""

    op.drop_index(
        "uq_asset_files_asset_id_checksum_sha256",
        table_name="asset_files",
    )

    op.create_unique_constraint(
        "uq_asset_files_asset_id_checksum_sha256",
        "asset_files",
        ["asset_id", "checksum_sha256"],
    )
