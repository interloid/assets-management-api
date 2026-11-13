from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.infrastructure.database import AsyncSessionLocal
from app.modules.asset.models import Asset
from app.modules.user.models import User
from app.shared.models.enums import UserRole


async def get_warranty_reminder_data() -> tuple[list[Asset], list[str]]:
    today = datetime.now(UTC).date()
    deadline = today + timedelta(days=30)

    async with AsyncSessionLocal() as session:
        asset_result = await session.execute(
            select(Asset)
            .where(
                Asset.warranty_expiry >= today,
                Asset.warranty_expiry <= deadline,
                Asset.deleted_at.is_(None),
            )
            .order_by(Asset.warranty_expiry.asc())
        )
        assets = list(asset_result.scalars().all())

        admin_result = await session.execute(
            select(User.email).where(
                User.role == UserRole.ADMIN, User.is_active.is_(True)
            )
        )
        admin_emails = list(admin_result.scalars().all())

    return assets, admin_emails
