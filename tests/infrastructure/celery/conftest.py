from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.celery import idempotency
from app.infrastructure.celery.app import celery_app
from app.infrastructure.celery.tasks.weekly_tasks import send_weekly_summary
from app.shared.models.enums import AssetStatus
from tests.config import test_settings

REPORT_DATE = date.today()
PURCHASE_DATE = REPORT_DATE - timedelta(days=30)
WARRANTY_EXPIRY = REPORT_DATE + timedelta(days=90)
CREATED_AT = datetime.combine(
    REPORT_DATE,
    datetime.min.time(),
    tzinfo=timezone.utc,
)
UPDATED_AT = CREATED_AT + timedelta(hours=1)


@pytest_asyncio.fixture
async def job_session_factory(monkeypatch):
    engine = create_async_engine(
        str(test_settings.TEST_DATABASE_URL),
        echo=False,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(idempotency, "AsyncSessionLocal", session_factory)

    try:
        yield session_factory
    finally:
        await engine.dispose()


@asynccontextmanager
async def fake_session(session):
    yield session


@asynccontextmanager
async def fake_context():
    yield


@pytest.fixture
def eager_celery(monkeypatch):
    monkeypatch.setitem(celery_app.conf, "task_always_eager", True)
    monkeypatch.setitem(celery_app.conf, "task_eager_propagates", True)


@pytest.fixture
def make_asset():
    return SimpleNamespace(
        asset_tag="IL-LAP-0001",
        type=SimpleNamespace(value="laptop"),
        status=SimpleNamespace(value="in_stock"),
        warranty_expiry=REPORT_DATE + timedelta(days=3),
    )


@pytest.fixture
def repair_asset():
    return SimpleNamespace(
        asset_tag="IL-LAP-0001",
        type=SimpleNamespace(value="laptop"),
        status=SimpleNamespace(value="repair"),
        warranty_expiry=REPORT_DATE + timedelta(days=19),
    )


@pytest.fixture
def warranty_asset():
    return SimpleNamespace(
        asset_tag="IL-MON-0002",
        type=SimpleNamespace(value="monitor"),
        status=SimpleNamespace(value="in_stock"),
        warranty_expiry=REPORT_DATE + timedelta(days=19),
    )


@pytest.fixture
def summary_data(repair_asset, warranty_asset):
    status_counts = {status: 0 for status in AssetStatus}
    status_counts[AssetStatus.IN_STOCK] = 1
    status_counts[AssetStatus.REPAIR] = 1

    return {
        "report_date": REPORT_DATE,
        "status_counts": status_counts,
        "repair_assets": [repair_asset],
        "warranty_assets": [warranty_asset],
        "admin_emails": [
            "admin1@example.com",
            "admin2@example.com",
        ],
    }


@pytest.fixture
def execute_weekly_summary():
    return lambda: send_weekly_summary.delay().get()
