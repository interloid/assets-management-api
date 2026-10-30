from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.background_jobs.repository import (
    BackgroundJobRepository,
)


class BackgroundJobCleanupService:
    RETENTION_DAYS = 90

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BackgroundJobRepository(session)

    async def cleanup_old_jobs(self) -> dict[str, int]:
        cutoff = datetime.now(UTC) - timedelta(
            days=self.RETENTION_DAYS,
        )

        try:
            deleted_count = await self.repository.delete_old_jobs(cutoff)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return {"deleted_background_jobs": deleted_count}
