from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.background_jobs.models import BackgroundJob


class BackgroundJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_old_jobs(self, cutoff: datetime) -> int:
        stmt = delete(BackgroundJob).where(
            BackgroundJob.status.in_(("completed", "failed")),
            BackgroundJob.completed_at.is_not(None),
            BackgroundJob.completed_at < cutoff,
        )

        result = await self.session.execute(stmt)

        return result.rowcount or 0
