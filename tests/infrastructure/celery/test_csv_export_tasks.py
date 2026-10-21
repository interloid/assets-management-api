import csv
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.celery.tasks.csv_export_tasks import (
    JOB_TYPE,
    run_asset_export,
)
from app.modules.asset.csv_export.csv_export_writter import (
    CSV_COLUMNS,
    asset_to_csv,
    csv_value,
    parse_filters,
    write_csv_file,
)
from app.shared.models.enums import AssetStatus, AssetType


@asynccontextmanager
async def fake_session(session):
    yield session


@asynccontextmanager
async def fake_context():
    yield


def test_csv_value_returns_empty_string_for_none():
    assert csv_value(None) == ""


def test_csv_value_converts_enum_to_value():
    assert csv_value(AssetType.LAPTOP) == AssetType.LAPTOP.value


def test_csv_value_converts_uuid_to_string():
    asset_id = uuid4()

    assert csv_value(asset_id) == str(asset_id)


def test_csv_value_converts_date_to_iso_format():
    assert csv_value(date(2026, 10, 25)) == "2026-10-25"


def test_csv_value_converts_datetime_to_iso_format():
    value = datetime(2026, 10, 21, 12, 30, tzinfo=timezone.utc)

    assert csv_value(value) == value.isoformat()


def test_parse_filters_converts_enum_and_uuid_values():
    user_id = uuid4()

    result = parse_filters(
        {
            "asset_type": AssetType.LAPTOP.value,
            "asset_status": AssetStatus.IN_STOCK.value,
            "assigned_to": str(user_id),
        }
    )

    assert result["asset_type"] == AssetType.LAPTOP
    assert result["asset_status"] == AssetStatus.IN_STOCK
    assert result["assigned_to"] == user_id


def test_parse_filters_preserves_unset_filters():
    filters = {
        "asset_type": None,
        "asset_status": None,
        "assigned_to": None,
        "search": "laptop",
    }

    result = parse_filters(filters)

    assert result == filters


def test_parse_filters_rejects_invalid_asset_type():
    with pytest.raises(ValueError):
        parse_filters({"asset_type": "not-a-valid-asset-type"})


def test_parse_filters_rejects_invalid_uuid():
    with pytest.raises(ValueError):
        parse_filters({"assigned_to": "not-a-uuid"})


def test_write_csv_file_writes_header_and_rows(tmp_path: Path):
    file_path = tmp_path / "assets.csv"
    rows = [
        {
            "id": uuid4(),
            "asset_tag": "IL-LAP-0001",
            "type": "laptop",
            "serial_number": "SN-001",
            "status": "in_stock",
            "assigned_user_name": None,
            "assigned_user_email": None,
            "purchase_date": date(2026, 1, 1),
            "warranty_expiry": date(2027, 1, 1),
            "notes": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
    ]

    count = write_csv_file(file_path, rows)

    assert count == 1
    assert file_path.exists()

    # utf-8-sig adds a BOM, so use utf-8-sig when reading.
    with file_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        exported_rows = list(reader)

    assert reader.fieldnames == CSV_COLUMNS
    assert len(exported_rows) == 1
    assert exported_rows[0]["asset_tag"] == "IL-LAP-0001"
    assert exported_rows[0]["type"] == "laptop"
    assert exported_rows[0]["status"] == "in_stock"
    assert exported_rows[0]["assigned_user_name"] == ""
    assert exported_rows[0]["purchase_date"] == "2026-01-01"


def test_write_csv_file_writes_header_for_empty_export(tmp_path: Path):
    file_path = tmp_path / "empty.csv"

    count = write_csv_file(file_path, [])

    assert count == 0

    with file_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        assert next(reader) == CSV_COLUMNS
        assert list(reader) == []


def test_asset_to_csv_handles_unassigned_asset():
    asset_id = uuid4()

    class FakeAsset:
        id = asset_id
        asset_tag = "IL-LAP-0001"
        type = AssetType.LAPTOP
        serial_number = "SN-001"
        status = AssetStatus.IN_STOCK
        assigned_user = None
        purchase_date = date(2026, 1, 1)
        warranty_expiry = date(2027, 1, 1)
        notes = None
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        updated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = asset_to_csv(FakeAsset())

    assert row["id"] == asset_id
    assert row["asset_tag"] == "IL-LAP-0001"
    assert row["assigned_user_name"] is None
    assert row["assigned_user_email"] is None


@pytest.mark.asyncio
async def test_run_asset_export_skips_unclaimed_job():
    export_id = uuid4()

    with patch(
        "app.infrastructure.celery.tasks.csv_export_tasks.claim_job",
        new_callable=AsyncMock,
        return_value=False,
    ) as mock_claim:
        result = await run_asset_export(
            export_id=export_id,
            task_id="task-123",
        )

    assert result == {
        "status": "skipped",
        "export_id": str(export_id),
    }

    mock_claim.assert_awaited_once_with(
        job_type=JOB_TYPE,
        idempotency_key=export_id,
        task_id="task-123",
    )


@pytest.mark.asyncio
async def test_run_asset_export_success(tmp_path):
    export_id = uuid4()
    task_id = "task-123"

    export = SimpleNamespace(
        id=export_id,
        filters={},
        status="pending",
    )

    session1 = MagicMock()
    session1.begin.return_value = fake_context()

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = export
    session1.execute = AsyncMock(return_value=query_result)

    session2 = MagicMock()
    session2.begin.return_value = fake_context()

    repository = MagicMock()
    repository.list_for_export = AsyncMock(
        return_value=[SimpleNamespace(asset_tag="IL-LAP-0001")]
    )

    with (
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.AsyncSessionLocal",
            side_effect=[
                fake_session(session1),
                fake_session(session2),
            ],
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.AssetRepository",
            return_value=repository,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.parse_filters",
            return_value={},
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.asset_to_csv",
            return_value={"asset_tag": "IL-LAP-0001"},
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.EXPORT_DIR",
            tmp_path,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.finish_export",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_finish,
    ):
        result = await run_asset_export(
            export_id=export_id,
            task_id=task_id,
        )

    expected_file = tmp_path / f"{export_id}-{task_id}.csv"

    assert result == {
        "status": "completed",
        "export_id": str(export_id),
        "assets_count": 1,
    }
    assert expected_file.exists()
    assert "IL-LAP-0001" in expected_file.read_text(encoding="utf-8-sig")
    mock_finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_asset_export_fails_when_export_not_found():
    export_id = uuid4()
    task_id = "task-missing"

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.begin.return_value = fake_context()
    session.execute = AsyncMock(return_value=query_result)

    with (
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.AsyncSessionLocal",
            return_value=fake_session(session),
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.mark_failed",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_mark_failed,
    ):
        with pytest.raises(
            ValueError,
            match=f"Export {export_id} was not found",
        ):
            await run_asset_export(
                export_id=export_id,
                task_id=task_id,
            )

    mock_mark_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_asset_export_marks_failure_when_csv_generation_fails(
    tmp_path,
):
    export_id = uuid4()
    task_id = "task-failure"

    export = SimpleNamespace(
        id=export_id,
        filters={},
        status="pending",
    )

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = export

    session1 = MagicMock()
    session1.begin.return_value = fake_context()
    session1.execute = AsyncMock(return_value=query_result)

    session2 = MagicMock()
    session2.begin.return_value = fake_context()

    repository = MagicMock()
    repository.list_for_export = AsyncMock(return_value=[])

    with (
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.claim_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.AsyncSessionLocal",
            side_effect=[
                fake_session(session1),
                fake_session(session2),
            ],
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.AssetRepository",
            return_value=repository,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.parse_filters",
            return_value={},
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.EXPORT_DIR",
            tmp_path,
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.write_csv_file",
            side_effect=OSError("Disk write failed"),
        ),
        patch(
            "app.infrastructure.celery.tasks.csv_export_tasks.mark_failed",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_mark_failed,
    ):
        with pytest.raises(OSError, match="Disk write failed"):
            await run_asset_export(
                export_id=export_id,
                task_id=task_id,
            )

    mock_mark_failed.assert_awaited_once()
    assert not (tmp_path / f"{export_id}-{task_id}.tmp").exists()
