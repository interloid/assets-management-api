from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.modules.asset.csv_export.csv_export_service import AssetExportService


@pytest.mark.asyncio
async def test_cleanup_expired_exports_returns_zero_counts(mock_session):
    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(return_value=[])

    result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 0,
        "missing_files": 0,
        "skipped_files": 0,
    }


@pytest.mark.asyncio
async def test_cleanup_expired_exports_deletes_valid_file(
    mock_session,
    tmp_path,
):
    export_file = tmp_path / "expired.csv"
    export_file.write_text("asset_tag\nIL-LAP-0001")

    export = SimpleNamespace(
        id=uuid4(),
        file_path=str(export_file),
    )

    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        return_value=[export],
    )

    with patch(
        "app.modules.asset.csv_export.csv_export_service.EXPORT_DIR",
        tmp_path,
    ):
        result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 1,
        "missing_files": 0,
        "skipped_files": 0,
    }
    assert not export_file.exists()


@pytest.mark.asyncio
async def test_cleanup_expired_exports_handles_missing_file(
    mock_session,
    tmp_path,
):
    export = SimpleNamespace(
        id=uuid4(),
        file_path=str(tmp_path / "missing.csv"),
    )

    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        return_value=[export],
    )

    with patch(
        "app.modules.asset.csv_export.csv_export_service.EXPORT_DIR",
        tmp_path,
    ):
        result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 0,
        "missing_files": 1,
        "skipped_files": 0,
    }


@pytest.mark.asyncio
async def test_cleanup_expired_exports_skips_invalid_path(
    mock_session,
    tmp_path,
):
    outside_file = tmp_path.parent / "outside.csv"
    outside_file.write_text("test")

    export = SimpleNamespace(
        id=uuid4(),
        file_path=str(outside_file),
    )

    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        return_value=[export],
    )

    with patch(
        "app.modules.asset.csv_export.csv_export_service.EXPORT_DIR",
        tmp_path,
    ):
        result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 0,
        "missing_files": 0,
        "skipped_files": 1,
    }
    assert outside_file.exists()


@pytest.mark.asyncio
async def test_cleanup_expired_exports_handles_os_error(
    mock_session,
    tmp_path,
):
    export_file = tmp_path / "expired.csv"
    export_file.write_text("test")

    export = SimpleNamespace(
        id=uuid4(),
        file_path=str(export_file),
    )

    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        return_value=[export],
    )

    with (
        patch(
            "app.modules.asset.csv_export.csv_export_service.EXPORT_DIR",
            tmp_path,
        ),
        patch.object(
            Path,
            "unlink",
            side_effect=OSError("Permission denied"),
        ),
    ):
        result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 0,
        "missing_files": 0,
        "skipped_files": 1,
    }


@pytest.mark.asyncio
async def test_cleanup_expired_exports_handles_multiple_results(
    mock_session,
    tmp_path,
):
    valid_file = tmp_path / "valid.csv"
    valid_file.write_text("test")

    missing_file = tmp_path / "missing.csv"

    outside_file = tmp_path.parent / "outside.csv"
    outside_file.write_text("test")

    exports = [
        SimpleNamespace(id=uuid4(), file_path=str(valid_file)),
        SimpleNamespace(id=uuid4(), file_path=str(missing_file)),
        SimpleNamespace(id=uuid4(), file_path=str(outside_file)),
    ]

    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        return_value=exports,
    )

    with patch(
        "app.modules.asset.csv_export.csv_export_service.EXPORT_DIR",
        tmp_path,
    ):
        result = await service.cleanup_expired_exports()

    assert result == {
        "deleted_files": 1,
        "missing_files": 1,
        "skipped_files": 1,
    }


@pytest.mark.asyncio
async def test_cleanup_expired_exports_propagates_repository_error(
    mock_session,
):
    service = AssetExportService(mock_session)
    service.repository.get_expired_exports = AsyncMock(
        side_effect=RuntimeError("Database unavailable"),
    )

    with pytest.raises(RuntimeError, match="Database unavailable"):
        await service.cleanup_expired_exports()
