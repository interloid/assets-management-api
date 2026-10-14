from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "assets_management",
    broker=str(settings.CELERY_BROKER_URL or settings.REDIS_URL),
    backend=str(settings.CELERY_RESULT_BACKEND or settings.REDIS_URL),
    include=["app.infrastructure.celery.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    request_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_trace_started=True,
)
