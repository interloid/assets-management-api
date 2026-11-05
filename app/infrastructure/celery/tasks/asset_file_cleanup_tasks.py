import asyncio
import logging

from app.infrastructure.celery.app import celery_app
from app.infrastructure.database import AsyncSessionLocal, engine
from app.modules.asset_files.service import AssetFileService

logger = logging.getLogger(__name__)


async def run_expired_asset_file_cleanup() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        service = AssetFileService(session)
        return await service.cleanup_expired_pending_uploads()


async def run_cleanup_with_engine_disposal() -> dict[str, int]:
    try:
        return await run_expired_asset_file_cleanup()
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name=(
        "app.infrastructure.celery.tasks.asset_file_cleanup_tasks.cleanup_expired_asset_files"
    ),
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_expired_asset_files(self) -> dict[str, int]:
    task_id = self.request.id

    try:
        result = asyncio.run(run_cleanup_with_engine_disposal())
        logger.info(
            "Expired asset-file cleanup finished. task_id=%s result=%s",
            task_id,
            result,
        )
        return result
    except Exception:
        logger.exception(
            "Expired asset-file cleanup task failed. task_id=%s",
            task_id,
        )
        raise
