from app.infrastructure.celery.app import celery_app


@celery_app.task(name="app.infrastructure.celery.tasks.add")
def add(a: int, b: int) -> int:
    return a + b
