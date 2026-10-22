from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.celery.tasks.weekly_tasks import (
    build_weekly_summary_digest,
)


def test_weekly_summary_success(
    eager_celery,
    summary_data,
    execute_weekly_summary,
):
    data = summary_data

    with (
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_claim_job,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.get_weekly_summary_data",
            new_callable=AsyncMock,
            return_value=data,
        ) as mock_get_data,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_mark_completed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.engine",
        ) as mock_engine,
    ):
        mock_engine.dispose = AsyncMock()
        result = execute_weekly_summary()

        report_date = data["report_date"]

        assert result == {
            "status": "success",
            "emails_sent": 2,
            "report_date": report_date.isoformat(),
        }

        recipients = [
            call.kwargs["recipient"] for call in mock_send_email.call_args_list
        ]

        assert recipients == [
            "admin1@example.com",
            "admin2@example.com",
        ]

        for call in mock_send_email.call_args_list:
            assert (
                call.kwargs["subject"]
                == f"Weekly Asset Management Summary - {report_date}"
            )
            assert "IL-LAP-0001" in call.kwargs["text_body"]
            assert "IL-MON-0002" in call.kwargs["text_body"]

        mock_mark_completed.assert_awaited_once()
        mock_mark_failed.assert_not_awaited()
        mock_claim_job.assert_awaited_once()
        mock_get_data.assert_awaited_once()
        assert mock_send_email.call_count == 2


def test_send_weekly_summary_without_admins(
    eager_celery, summary_data, execute_weekly_summary
):
    data = summary_data
    data["admin_emails"] = []

    with (
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_claim_job,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.get_weekly_summary_data",
            new_callable=AsyncMock,
            return_value=data,
        ) as mock_get_data,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_mark_completed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.engine",
        ) as mock_engine,
    ):
        mock_engine.dispose = AsyncMock()
        result = execute_weekly_summary()

        assert result == {
            "status": "no_admins",
            "emails_sent": 0,
            "report_date": data["report_date"].isoformat(),
        }

        mock_claim_job.assert_awaited_once()
        mock_get_data.assert_awaited_once()
        mock_send_email.assert_not_called()
        mock_mark_completed.assert_awaited_once()
        mock_mark_failed.assert_not_awaited()


def test_send_weekly_summary_skips_duplicate_job(
    eager_celery,
    execute_weekly_summary,
):
    with (
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_claim_job,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.get_weekly_summary_data",
            new_callable=AsyncMock,
        ) as mock_get_data,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_completed",
            new_callable=AsyncMock,
        ) as mock_mark_completed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.engine",
        ) as mock_engine,
    ):
        mock_engine.dispose = AsyncMock()
        result = execute_weekly_summary()

        assert result == {
            "status": "skipped",
            "emails_sent": 0,
        }

        mock_claim_job.assert_awaited_once()
        mock_get_data.assert_not_awaited()
        mock_send_email.assert_not_called()
        mock_mark_completed.assert_not_awaited()
        mock_mark_failed.assert_not_awaited()


def test_send_weekly_summary_records_data_retrieval_failure(
    eager_celery,
    execute_weekly_summary,
):
    with (
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_claim_job,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.get_weekly_summary_data",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Database unavailable"),
        ) as mock_get_data,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_completed",
            new_callable=AsyncMock,
        ) as mock_mark_completed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.engine",
        ) as mock_engine,
    ):
        mock_engine.dispose = AsyncMock()

        with pytest.raises(RuntimeError, match="Database unavailable"):
            execute_weekly_summary()

        mock_claim_job.assert_awaited_once()
        mock_get_data.assert_awaited_once()
        mock_send_email.assert_not_called()
        mock_mark_completed.assert_not_awaited()
        mock_mark_failed.assert_awaited_once()

        failure = mock_mark_failed.await_args.kwargs
        assert failure["job_type"] == "weekly_summary"
        assert failure["error"] == "Database unavailable"


def test_send_weekly_summary_records_completion_failure(
    eager_celery,
    summary_data,
    execute_weekly_summary,
):
    data = summary_data

    with (
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_claim_job,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.get_weekly_summary_data",
            new_callable=AsyncMock,
            return_value=data,
        ) as mock_get_data,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_mark_completed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.mark_failed",
            new_callable=AsyncMock,
        ) as mock_mark_failed,
        patch(
            "app.infrastructure.celery.tasks.weekly_tasks.engine",
        ) as mock_engine,
    ):
        mock_engine.dispose = AsyncMock()

        with pytest.raises(
            RuntimeError,
            match="Could not mark weekly summary job as completed",
        ):
            execute_weekly_summary()

        mock_claim_job.assert_awaited_once()
        mock_get_data.assert_awaited_once()
        assert mock_send_email.call_count == 2
        mock_mark_completed.assert_awaited_once()
        mock_mark_failed.assert_awaited_once()

        failure = mock_mark_failed.await_args.kwargs
        assert failure["job_type"] == "weekly_summary"
        assert failure["error"] == "Could not mark weekly summary job as completed"


def test_build_weekly_summary_digest_contains_asset_details(summary_data):
    digest = build_weekly_summary_digest(summary_data)

    assert "Weekly Asset Management Summary" in digest
    assert f"Report date: {summary_data['report_date']}" in digest
    assert "ASSETS COUNT BY STATUS" in digest
    assert "repair: 1" in digest
    assert "ASSETS IN REPAIR: 1" in digest
    assert "IL-LAP-0001 (laptop)" in digest
    assert "UPCOMING WARRANTY EXPIRES (NEXT 30 DAYS): 1" in digest
    assert (
        f"IL-MON-0002 (monitor) - expires "
        f"{summary_data['warranty_assets'][0].warranty_expiry}" in digest
    )


def test_build_weekly_summary_digest_without_assets(summary_data):
    data = summary_data.copy()
    data["repair_assets"] = []
    data["warranty_assets"] = []

    digest = build_weekly_summary_digest(data)

    assert "ASSETS IN REPAIR: 0" in digest
    assert "No assets are currently in repair" in digest
    assert "UPCOMING WARRANTY EXPIRES (NEXT 30 DAYS): 0" in digest
    assert "No warranties expire within the next 30 days." in digest
