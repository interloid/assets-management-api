import asyncio
import logging

from app.infrastructure.celery.app import celery_app
from app.infrastructure.database import AsyncSessionLocal, engine
from app.modules.auth.services import AuthService

logger = logging.getLogger(__name__)


async def run_refresh_token_cleanup() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        service = AuthService(session)

        return await service.cleanup_expired_refresh_tokens()


async def run_cleanup_with_engine_disposal() -> dict[str, int]:
    try:
        return await run_refresh_token_cleanup()
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name=(
        "app.infrastructure.celery.tasks.refresh_token_cleanup_tasks.cleanup_expired_refresh_tokens"
    ),
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_expired_refresh_tokens(self) -> dict[str, int]:
    task_id = self.request.id

    try:
        result = asyncio.run(run_cleanup_with_engine_disposal())

        logger.info(
            "Expired refresh-token cleanup finished. task_id=%s result=%s",
            task_id,
            result,
        )

        return result

    except Exception:
        logger.exception(
            "Expired refresh-token cleanup task failed. task_id=%s",
            task_id,
        )
        raise
