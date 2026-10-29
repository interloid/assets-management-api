import asyncio
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.celery.tasks.csv_export_tasks import (
    EXPORT_DIR,
    generate_asset_csv,
)
from app.modules.asset.csv_export.csv_export_exception import (
    ExportFileNotFoundError,
    ExportNotFoundError,
    ExportNotReadyError,
    ExportQueueError,
    InvalidExportPathError,
)
from app.modules.asset.csv_export.csv_export_model import AssetExport
from app.modules.asset.csv_export.csv_export_repository import AssetExportRepository


def validate_export_file_path(file_path: str) -> Path:
    export_root = EXPORT_DIR.resolve()
    resolved_path = Path(file_path).resolve()

    if not resolved_path.is_relative_to(export_root):
        raise InvalidExportPathError()

    if not resolved_path.is_file():
        raise ExportFileNotFoundError()

    return resolved_path


class AssetExportService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.repository = AssetExportRepository(session)

    async def create_export(
        self,
        requested_by: UUID,
        filters: dict,
        request_id: str | None = None,
    ) -> AssetExport:
        export = AssetExport(
            requested_by=requested_by,
            status="pending",
            filters=filters,
        )

        await self.repository.create(export)
        await self.session.commit()
        await self.session.refresh(export)

        try:
            generate_asset_csv.apply_async(
                args=[str(export.id)],
                kwargs={"request_id": request_id},
            )
        except Exception as exc:
            await self.repository.update_status(export.id, "failed")
            await self.session.commit()
            raise ExportQueueError() from exc

        return export

    async def get_export(
        self,
        export_id: UUID,
    ) -> AssetExport:

        export = await self.repository.get_by_id(export_id)

        if export is None:
            raise ExportNotFoundError()

        return export

    async def get_download_path(
        self,
        export_id: UUID,
    ) -> Path:
        export = await self.get_export(export_id)

        if export.status != "completed" or not export.file_path:
            raise ExportNotReadyError()

        return await asyncio.to_thread(
            validate_export_file_path,
            export.file_path,
        )
