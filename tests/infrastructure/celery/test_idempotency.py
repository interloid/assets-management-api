from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.infrastructure.celery.idempotency import (
    STALE_JOB_TIMEOUT,
    claim_job,
    mark_completed,
    mark_failed,
)
from app.modules.asset.models import Asset  # noqa: F401
from app.modules.asset.tag.model import AssetTagCounter  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.user.models import User  # noqa: F401
from app.shared.background_jobs.models import BackgroundJob


async def get_job(
    job_session_factory,
    job_type: str,
    idempotency_key,
) -> BackgroundJob:
    async with job_session_factory() as session:
        result = await session.execute(
            select(BackgroundJob).where(
                BackgroundJob.job_type == job_type,
                BackgroundJob.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_claim_new_job(job_session_factory):
    key = uuid4()

    claimed = await claim_job("test_job", key, "task-1")

    assert claimed is True

    job = await get_job(job_session_factory, "test_job", key)

    assert job.status == "running"
    assert job.task_id == "task-1"
    assert job.started_at is not None


@pytest.mark.asyncio
async def test_dupliacte_claim_is_rejected(job_session_factory):
    key = uuid4()

    first_claim = await claim_job("test_job", key, "task-1")
    second_claim = await claim_job("test_job", key, "task-2")

    assert first_claim is True
    assert second_claim is False

    job = await get_job(job_session_factory, "test_job", key)
    assert job.task_id == "task-1"
    assert job.status == "running"


@pytest.mark.asyncio
async def test_completed_job_cannot_be_claimed_again(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True
    assert await mark_completed("test_job", key, "task-1") is True

    claimed_again = await claim_job("test_job", key, "task-2")

    assert claimed_again is False

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "completed"
    assert job.task_id == "task-1"


@pytest.mark.asyncio
async def test_failed_job_can_be_reclaimed(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True
    assert await mark_failed("test_job", key, "task-1", "Temporary error") is True

    reclaimed = await claim_job("test_job", key, "task-2")

    assert reclaimed is True

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "running"
    assert job.task_id == "task-2"
    assert job.last_error is None
    assert job.completed_at is None


@pytest.mark.asyncio
async def test_stale_running_job_can_be_reclaimed(job_session_factory):
    key = uuid4()

    stale_started_at = datetime.now(UTC) - STALE_JOB_TIMEOUT - timedelta(seconds=1)

    async with job_session_factory() as session:
        async with session.begin():
            session.add(
                BackgroundJob(
                    job_type="test_job",
                    idempotency_key=key,
                    status="running",
                    task_id="old-task",
                    started_at=stale_started_at,
                )
            )

    reclaimed = await claim_job("test_job", key, "new-task")

    assert reclaimed is True

    job = await get_job(job_session_factory, "test_job", key)

    assert job.status == "running"
    assert job.task_id == "new-task"
    assert job.started_at > stale_started_at


@pytest.mark.asyncio
async def test_recent_running_job_cannot_be_reclaimed(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True

    reclaimed = await claim_job("test_job", key, "task-2")

    assert reclaimed is False

    job = await get_job(job_session_factory, "test_job", key)
    assert job.task_id == "task-1"


@pytest.mark.asyncio
async def test_mark_completed_successfully(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True

    completed = await mark_completed("test_job", key, "task-1")

    assert completed is True

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "completed"
    assert job.completed_at is not None
    assert job.last_error is None


@pytest.mark.asyncio
async def test_mark_failed_successfully(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True

    failed = await mark_failed("test_job", key, "task-1", "SMTP connection failed")

    assert failed is True

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "failed"
    assert job.last_error == "SMTP connection failed"


@pytest.mark.asyncio
async def test_wrong_task_id_cannot_complete_job(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True

    completed = await mark_completed("test_job", key, "wrong-task")

    assert completed is False

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "running"
    assert job.task_id == "task-1"


@pytest.mark.asyncio
async def test_wrong_task_id_cannot_fail_job(job_session_factory):
    key = uuid4()

    assert await claim_job("test_job", key, "task-1") is True

    failed = await mark_failed("test_job", key, "wrong-task", "Unexpected error")

    assert failed is False

    job = await get_job(job_session_factory, "test_job", key)
    assert job.status == "running"
    assert job.task_id == "task-1"
    assert job.last_error is None
