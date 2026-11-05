"""Add missing asset file upload statuses."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "00795637e0fc"
down_revision = "b44118a4892e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE file_upload_status ADD VALUE IF NOT EXISTS 'failed'")
    op.execute("ALTER TYPE file_upload_status ADD VALUE IF NOT EXISTS 'deleted'")


def downgrade() -> None:
    # PostgreSQL does not directly support removing enum values.
    pass
