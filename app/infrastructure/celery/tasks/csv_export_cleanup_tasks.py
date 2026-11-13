import asyncio
import logging

from app.infrastructure.celery.app import celery_app
from app.infrastructure.database import AsyncSessionLocal, engine
from app.modules.asset.csv_export.csv_export_service import AssetExportService

logger = logging.getLogger(__name__)


async def run_csv_export_cleanup() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        service = AssetExportService(session)
        return await service.cleanup_expired_exports()


async def run_cleanup_with_engine_disposal() -> dict[str, int]:
    try:
        return await run_csv_export_cleanup()
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name=(
        "app.infrastructure.celery.tasks.csv_export_cleanup_tasks."
        "cleanup_expired_csv_exports"
    ),
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_expired_csv_exports(self) -> dict[str, int]:
    task_id = self.request.id

    try:
        result = asyncio.run(run_cleanup_with_engine_disposal())

        logger.info(
            "Expired CSV export cleanup completed. task_id=%s result=%s",
            task_id,
            result,
        )

        return result

    except Exception:
        logger.exception(
            "Expired CSV export cleanup failed. task_id=%s",
            task_id,
        )
        raise
