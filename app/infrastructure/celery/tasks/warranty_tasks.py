import asyncio
import logging
import smtplib
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from app.infrastructure.celery.app import celery_app
from app.infrastructure.celery.idempotency import (
    claim_job,
    mark_completed,
    mark_failed,
)
from app.infrastructure.database import engine
from app.infrastructure.email import send_email
from app.modules.asset.models import Asset  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.notifications.warranty_reminders import get_warranty_reminder_data
from app.modules.user.models import User  # noqa: F401

logger = logging.getLogger(__name__)


async def run_warranty_reminder(
    task_id: str,
    idempotency_key,
) -> dict:
    job_type = "warranty_reminder"

    try:
        claimed = await claim_job(
            job_type=job_type,
            idempotency_key=idempotency_key,
            task_id=task_id,
        )

        if not claimed:
            return {
                "status": "skipped",
                "emails_sent": 0,
            }

        assets, admin_emails = await get_warranty_reminder_data()

        if not admin_emails:
            await mark_completed(
                job_type,
                idempotency_key,
                task_id,
            )
            return {
                "status": "no_admins",
                "emails_sent": 0,
            }

        if assets:
            subject = f"Warranty Expiry Reminder - {len(assets)} asset(s)"
        else:
            subject = "Daily Warranty Report - No Upcomming Expirations"

        digest = build_digest(assets)
        emails_sent = 0

        for email in admin_emails:
            send_email(recipient=email, subject=subject, text_body=digest)
            emails_sent += 1

        completed = await mark_completed(
            job_type,
            idempotency_key,
            task_id,
        )

        if not completed:
            raise RuntimeError(
                "Could not mark warranty reminder job as completed",
            )

        return {
            "status": "success",
            "assets_count": len(assets),
            "emails_sent": emails_sent,
        }

    except Exception as exc:
        try:
            await mark_failed(
                job_type=job_type,
                idempotency_key=idempotency_key,
                task_id=task_id,
                error=str(exc),
            )
        except Exception:
            logger.exception(
                "Failed to record warranty reminder failure. task_id=%s", task_id
            )
        raise


async def run_warranty_reminder_with_cleanup(
    task_id: str,
    idempotency_key,
) -> dict:
    try:
        return await run_warranty_reminder(
            task_id=task_id,
            idempotency_key=idempotency_key,
        )
    finally:
        await engine.dispose()


def build_digest(assets) -> str:
    if not assets:
        return (
            "Daily Warranty Status Report\n\n"
            "There are currently no active assets with warranties "
            "expiring within the next 30 days.\n\n"
            "Assets Management API"
        )
    lines = [
        "Warranty Expiry Reminders",
        "",
        "The following assets have warranties expiring within 30 days:",
        "",
    ]

    for asset in assets:
        lines.extend(
            [
                f"Asset Tag: {asset.asset_tag}",
                f"Type: {asset.type.value}",
                f"Asset Status: {asset.status.value}",
                f"Warranty Expiry: {asset.warranty_expiry}",
                "",
            ]
        )

    lines.extend(
        [
            "Please review these assets and take any neccessary actions",
            "",
            "Assets Management API",
        ]
    )

    return "\n".join(lines)


@celery_app.task(
    bind=True,
    name="app.infrastructure.celery.tasks.warranty_tasks.send_warranty_reminders",
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_warranty_reminders(self) -> dict:
    task_id = self.request.id
    run_date = datetime.now(UTC).date().isoformat()

    idempotency_key = uuid5(NAMESPACE_URL, f"warranty-reminder:{run_date}")

    try:
        return asyncio.run(
            run_warranty_reminder(
                task_id=task_id,
                idempotency_key=idempotency_key,
            )
        )

    except Exception:
        logger.exception(
            "Warranty reminder task failed. task_id=%s",
            task_id,
        )
        raise
