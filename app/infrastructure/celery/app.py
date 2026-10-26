from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "assets_management",
    broker=str(settings.CELERY_BROKER_URL or settings.REDIS_URL),
    backend=str(settings.CELERY_RESULT_BACKEND or settings.REDIS_URL),
    include=[
        "app.infrastructure.celery.tasks.warranty_tasks",
        "app.infrastructure.celery.tasks.csv_export_tasks",
        "app.infrastructure.celery.tasks.weekly_tasks",
        "app.infrastructure.celery.tasks.asset_file_cleanup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    request_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_trace_started=True,
    beat_schedule={
        "daily-warranty-expiry-reminders": {
            "task": "app.infrastructure.celery.tasks.warranty_tasks.send_warranty_reminders",
            "schedule": crontab(hour=12, minute=30),
        },
        "weekly-asset-management-summary": {
            "task": "app.infrastructure.celery.tasks.weekly_tasks.send_weekly_summary",
            "schedule": crontab(hour=5, minute=35, day_of_week="thursday"),
        },
        "daily-expired-asset-file-cleanup": {
            "task": (
                "app.infrastructure.celery.tasks.asset_file_cleanup_tasks.cleanup_expired_asset_files"
            ),
            "schedule": crontab(hour=1, minute=0),
        },
    },
)
