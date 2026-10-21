from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.asset.csv_export.csv_export_model import AssetExport


class AssetExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, export: AssetExport) -> AssetExport:
        self.session.add(export)
        await self.session.flush()
        return export

    async def get_by_id(
        self,
        export_id: UUID,
    ) -> AssetExport | None:
        return await self.session.get(AssetExport, export_id)

    async def update_status(
        self,
        export_id: UUID,
        new_status: str,
    ) -> None:
        await self.session.execute(
            update(AssetExport)
            .where(AssetExport.id == export_id)
            .values(status=new_status)
        )
