from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.celery.app import celery_app
from app.infrastructure.celery.warranty_tasks import (
    build_digest,
    send_warranty_reminders,
)


@pytest.fixture
def eager_celery(monkeypatch):
    monkeypatch.setitem(
        celery_app.conf,
        "task_always_eager",
        True,
    )
    monkeypatch.setitem(
        celery_app.conf,
        "task_eager_propagates",
        True,
    )


def make_asset():
    return SimpleNamespace(
        asset_tag="IL-LAP-0001",
        type=SimpleNamespace(value="laptop"),
        status=SimpleNamespace(value="in_stock"),
        warranty_expiry=date(2026, 10, 25),
    )


def test_send_warranty_reminders_success(eager_celery):
    assets = [make_asset()]
    admins = ["admin@example.com"]

    with (
        patch(
            "app.infrastructure.celery.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=(assets, admins),
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_failed",
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


def test_send_warranty_reminders_without_admins(eager_celery):
    with (
        patch(
            "app.infrastructure.celery.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=([make_asset()], []),
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_failed",
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
            "app.infrastructure.celery.warranty_tasks.get_warranty_reminder_data",
            new_callable=AsyncMock,
            return_value=([], ["admin@example.com"]),
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.send_email",
        ) as mock_send_email,
        patch(
            "app.infrastructure.celery.warranty_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_completed",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.warranty_tasks.mark_failed",
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


def test_build_digest_contains_asset_details():
    result = build_digest([make_asset()])

    assert "IL-LAP-0001" in result
    assert "laptop" in result
    assert "in_stock" in result
    assert "2026-10-25" in result


def test_build_digest_without_assets():
    result = build_digest([])

    assert "Daily Warranty Status Report" in result
    assert "no active assets" in result.lower()
