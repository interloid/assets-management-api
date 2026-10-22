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
from app.modules.notifications.weekly_summary import (
    get_weekly_summary_data,
)
from app.modules.user.models import User  # noqa: F401
from app.shared.models.enums import AssetStatus

logger = logging.getLogger(__name__)


async def run_weekly_summary(
    task_id: str,
    idempotency_key,
) -> dict:
    job_type = "weekly_summary"

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
        data = await get_weekly_summary_data()
        admin_emails = data["admin_emails"]
        digest = build_weekly_summary_digest(data)
        emails_sent = 0

        for email in admin_emails:
            send_email(
                recipient=email,
                subject=f"Weekly Asset Management Summary - {data['report_date']}",
                text_body=digest,
            )

            emails_sent += 1

        if not await mark_completed(job_type, idempotency_key, task_id):
            raise RuntimeError("Could not mark weekly summary job as completed")

        return {
            "status": "success" if admin_emails else "no_admins",
            "emails_sent": emails_sent,
            "report_date": data["report_date"].isoformat(),
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
                "Failed to record weekly summary failure. task_id=%s",
                task_id,
            )
        raise


async def run_weekly_summary_with_cleanup(
    task_id: str,
    idempotency_key,
) -> dict:
    try:
        return await run_weekly_summary(
            task_id=task_id, idempotency_key=idempotency_key
        )

    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="app.infrastructure.celery.tasks.weekly_tasks.send_weekly_summary",
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_weekly_summary(self) -> dict:
    task_id = self.request.id
    now = datetime.now(UTC)
    iso_year, iso_week, _ = now.isocalendar()
    idempotency_key = uuid5(NAMESPACE_URL, f"weekly-summary:{iso_year}-W{iso_week:02d}")

    try:
        return asyncio.run(
            run_weekly_summary_with_cleanup(
                task_id=task_id,
                idempotency_key=idempotency_key,
            )
        )
    except Exception:
        logger.exception(
            "Weekly summary task failed. task_id=%s",
            task_id,
        )
        raise


def build_weekly_summary_digest(data: dict) -> str:
    report_date = data["report_date"]
    status_counts = data["status_counts"]
    repair_assets = data["repair_assets"]
    warranty_assets = data["warranty_assets"]

    lines = [
        "Weekly Asset Management Summary",
        f"Report date: {report_date}",
        "",
        "ASSETS COUNT BY STATUS",
    ]

    for status in AssetStatus:
        lines.append(f"{status.value}: {status_counts[status]}")

    lines.extend(["", f"ASSETS IN REPAIR: {len(repair_assets)}"])

    if repair_assets:
        for asset in repair_assets:
            lines.append(f"- {asset.asset_tag} ({asset.type.value})")

    else:
        lines.append("No assets are currently in repair")

    lines.extend(
        [
            "",
            f"UPCOMING WARRANTY EXPIRES (NEXT 30 DAYS): {len(warranty_assets)}",
        ]
    )

    if warranty_assets:
        for asset in warranty_assets:
            lines.append(
                f"- {asset.asset_tag} ({asset.type.value}) "
                f"- expires {asset.warranty_expiry}"
            )
    else:
        lines.append("No warranties expire within the next 30 days.")

    lines.extend(["", "Assets Management API"])

    return "\n".join(lines)
