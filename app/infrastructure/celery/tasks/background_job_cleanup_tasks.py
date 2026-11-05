import asyncio
import logging

from app.infrastructure.celery.app import celery_app
from app.infrastructure.database import AsyncSessionLocal, engine
from app.shared.background_jobs.service import BackgroundJobCleanupService

logger = logging.getLogger(__name__)


async def run_background_job_cleanup() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        service = BackgroundJobCleanupService(session)

        return await service.cleanup_old_jobs()


async def run_cleanup_with_engine_disposal() -> dict[str, int]:
    try:
        return await run_background_job_cleanup()
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name=(
        "app.infrastructure.celery.tasks.background_job_cleanup_tasks.cleanup_expired_background_jobs"
    ),
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_expired_background_jobs(self) -> dict[str, int]:
    task_id = self.request.id

    try:
        result = asyncio.run(run_cleanup_with_engine_disposal())

        logger.info(
            "Expired background-job cleanup finished. task_id=%s result=%s",
            task_id,
            result,
        )

        return result

    except Exception:
        logger.exception(
            "Expired background-job cleanup task failed. task_id=%s",
            task_id,
        )
        raise
