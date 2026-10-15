import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, update
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.database import AsyncSessionLocal
from app.shared.models.background_job import BackgroundJob

logger = logging.getLogger(__name__)

STALE_JOB_TIMEOUT = timedelta(minutes=30)


async def claim_job(
    job_type: str,
    idempotency_key: UUID,
    task_id: str,
) -> bool:
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = (
                insert(BackgroundJob)
                .values(
                    job_type=job_type,
                    idempotency_key=idempotency_key,
                    status="running",
                    task_id=task_id,
                    started_at=now,
                    last_error=None,
                )
                .on_conflict_do_nothing(constraint="uq_background_job_type_key")
                .returning(BackgroundJob.id)
            )

            result = await session.execute(stmt)

            if result.scalar_one_or_none() is not None:
                logger.info(
                    "Background job claimed. job_type=%s task_id=%s",
                    job_type,
                    task_id,
                )
                return True

            stale_before = now - STALE_JOB_TIMEOUT
            stmt = (
                update(BackgroundJob)
                .where(
                    BackgroundJob.job_type == job_type,
                    BackgroundJob.idempotency_key == idempotency_key,
                    or_(
                        BackgroundJob.status.in_(["pending", "failed"]),
                        and_(
                            BackgroundJob.status == "running",
                            BackgroundJob.started_at < stale_before,
                        ),
                    ),
                )
                .values(
                    status="running",
                    task_id=task_id,
                    started_at=now,
                    completed_at=None,
                    last_error=None,
                )
                .returning(BackgroundJob.id)
            )

            result = await session.execute(stmt)
            claimed = result.scalar_one_or_none() is not None

            if claimed:
                logger.info(
                    "Background job reclaimed. job_type=%s task_id=%s",
                    job_type,
                    task_id,
                )
            else:
                logger.info(
                    "Background job skipped; already claimed or completed. "
                    "job_type=%s task_id=%s",
                    job_type,
                    task_id,
                )

            return claimed


async def mark_completed(
    job_type: str,
    idempotency_key: UUID,
    task_id: str,
) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = (
                update(BackgroundJob)
                .where(
                    BackgroundJob.job_type == job_type,
                    BackgroundJob.idempotency_key == idempotency_key,
                    BackgroundJob.task_id == task_id,
                    BackgroundJob.status == "running",
                )
                .values(
                    status="completed",
                    completed_at=datetime.now(UTC),
                    last_error=None,
                )
                .returning(BackgroundJob.id)
            )

            result = await session.execute(stmt)
            completed = result.scalar_one_or_none() is not None

    if completed:
        logger.info(
            "Background job completed. job_type=%s  task_id=%s",
            job_type,
            task_id,
        )
    return completed


async def mark_failed(
    job_type: str,
    idempotency_key: UUID,
    task_id: str,
    error: str,
) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = (
                update(BackgroundJob)
                .where(
                    BackgroundJob.job_type == job_type,
                    BackgroundJob.idempotency_key == idempotency_key,
                    BackgroundJob.task_id == task_id,
                    BackgroundJob.status == "running",
                )
                .values(
                    status="failed",
                    last_error=error[:4000],
                )
                .returning(BackgroundJob.id)
            )

            result = await session.execute(stmt)
            failed = result.scalar_one_or_none() is not None

    if failed:
        logger.error(
            "Background job failed. job_type=%s task_id=%s error=%s",
            job_type,
            task_id,
            error,
        )
    else:
        logger.warning(
            "Could not mark background job as failed. job_typ=%s task_id=%s",
            job_type,
            task_id,
        )

    return failed
