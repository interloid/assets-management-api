from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.infrastructure.database import AsyncSessionLocal
from app.modules.asset.models import Asset
from app.modules.user.models import User
from app.shared.models.enums import AssetStatus, UserRole


async def get_weekly_summary_data() -> dict:
    today = datetime.now(UTC).date()
    deadline = today + timedelta(days=30)

    async with AsyncSessionLocal() as session:
        status_result = await session.execute(
            select(Asset.status, func.count(Asset.id))
            .where(Asset.deleted_at.is_(None))
            .group_by(Asset.status)
        )

        status_counts = {status: 0 for status in AssetStatus}
        for status, count in status_result.all():
            status_counts[status] = count

        repair_result = await session.execute(
            select(Asset)
            .where(
                Asset.status == AssetStatus.REPAIR,
                Asset.deleted_at.is_(None),
            )
            .order_by(Asset.asset_tag.asc())
        )

        repair_assets = list(repair_result.scalars().all())

        warranty_result = await session.execute(
            select(Asset)
            .where(
                Asset.warranty_expiry >= today,
                Asset.warranty_expiry <= deadline,
                Asset.deleted_at.is_(None),
            )
            .order_by(Asset.warranty_expiry.asc())
        )
        warranty_assets = list(warranty_result.scalars().all())

        admin_result = await session.execute(
            select(User.email).where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
        )

        admin_emails = list(admin_result.scalars().all())

        return {
            "report_date": today,
            "status_counts": status_counts,
            "repair_assets": repair_assets,
            "warranty_assets": warranty_assets,
            "admin_emails": admin_emails,
        }
