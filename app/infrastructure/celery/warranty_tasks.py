import asyncio
import smtplib

from app.infrastructure.celery.app import celery_app
from app.infrastructure.database import engine
from app.infrastructure.email import send_email
from app.modules.asset.models import Asset  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.notifications.warranty_reminders import get_warranty_reminder_data
from app.modules.user.models import User  # noqa: F401


def get_reminder_data():
    async def fetch_data():
        try:
            return await get_warranty_reminder_data()
        finally:
            await engine.dispose()

    return asyncio.run(fetch_data())


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
    name="app.infrastructure.celery.warranty_tasks.send_warranty_reminders",
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_warranty_reminders() -> dict:
    assets, admin_emails = get_reminder_data()

    if not admin_emails:
        return {
            "status": "no_admins",
            "emails_sent": 0,
        }

    if assets:
        subject = f"Warranty Expiry Reminder - {len(assets)} asset(s)"
    else:
        subject = "Daily Warranty Report - No Upcoming Expirations"
    digest = build_digest(assets)
    emails_sent = 0

    for email in admin_emails:
        send_email(recipient=email, subject=subject, text_body=digest)
        emails_sent += 1

    return {
        "status": "success",
        "assets_count": len(assets),
        "emails_sent": emails_sent,
    }
