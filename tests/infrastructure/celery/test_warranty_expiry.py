from unittest.mock import AsyncMock, patch

from app.infrastructure.celery.tasks.warranty_tasks import (
    build_digest,
    send_warranty_reminders,
)


def test_send_warranty_reminders_success(eager_celery, make_asset):
    assets = [make_asset]
    admins = ["admin@example.com"]

    with (
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=(assets, admins),
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_failed",
            new_callable=AsyncMock,
        ),
    ):
        result = send_warranty_reminders.delay().get()

    assert result == {
        "status": "success",
        "assets_count": 1,
        "emails_sent": 1,
    }

    mock_send_email.assert_called_once()
    assert mock_send_email.call_args.kwargs["recipient"] == "admin@example.com"

    assert "IL-LAP-0001" in (mock_send_email.call_args.kwargs["text_body"])


def test_send_warranty_reminders_without_admins(eager_celery, make_asset):
    with (
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=([make_asset], []),
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_failed",
            new_callable=AsyncMock,
        ),
    ):
        result = send_warranty_reminders.delay().get()

    assert result == {
        "status": "no_admins",
        "emails_sent": 0,
    }
    mock_send_email.assert_not_called()


def test_send_warranty_reminders_without_expiring_assets(
    eager_celery,
):
    with (
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=([], ["admin@example.com"]),
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.warranty_tasks.mark_failed",
            new_callable=AsyncMock,
        ),
    ):
        result = send_warranty_reminders.delay().get()

    assert result == {
        "status": "success",
        "assets_count": 0,
        "emails_sent": 1,
    }

    mock_send_email.assert_called_once()
    assert (
        mock_send_email.call_args.kwargs["subject"]
        == "Daily Warranty Report - No Upcomming Expirations"
    )


def test_build_digest_contains_asset_details(make_asset):
    result = build_digest([make_asset])

    assert "IL-LAP-0001" in result
    assert "laptop" in result
    assert "in_stock" in result
    assert str(make_asset.warranty_expiry) in result


def test_build_digest_without_assets():
    result = build_digest([])

    assert "Daily Warranty Status Report" in result
    assert "no active assets" in result.lower()
