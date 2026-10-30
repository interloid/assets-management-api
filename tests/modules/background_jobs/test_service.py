from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.shared.background_jobs.service import BackgroundJobCleanupService


@pytest.fixture
def session():
    mock_session = AsyncMock()
    return mock_session


@pytest.mark.asyncio
async def test_cleanup_old_jobs_success(session):
    with patch(
        "app.shared.background_jobs.service.BackgroundJobRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.delete_old_jobs = AsyncMock(return_value=5)

        before = datetime.now(UTC)

        service = BackgroundJobCleanupService(session)
        result = await service.cleanup_old_jobs()

        after = datetime.now(UTC)

        cutoff = repository.delete_old_jobs.await_args.args[0]

        assert result == {"deleted_background_jobs": 5}
        assert before - timedelta(days=90) <= cutoff
        assert cutoff <= after - timedelta(days=90)

        repository.delete_old_jobs.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_old_jobs_returns_zero_when_no_jobs_deleted(session):
    with patch(
        "app.shared.background_jobs.service.BackgroundJobRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.delete_old_jobs = AsyncMock(return_value=0)

        service = BackgroundJobCleanupService(session)
        result = await service.cleanup_old_jobs()

        assert result == {"deleted_background_jobs": 0}

        repository.delete_old_jobs.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_old_jobs_rolls_back_on_repository_error(session):
    with patch(
        "app.shared.background_jobs.service.BackgroundJobRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.delete_old_jobs = AsyncMock(side_effect=Exception("Database error"))

        service = BackgroundJobCleanupService(session)

        with pytest.raises(Exception, match="Database error"):
            await service.cleanup_old_jobs()

        repository.delete_old_jobs.assert_awaited_once()
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
