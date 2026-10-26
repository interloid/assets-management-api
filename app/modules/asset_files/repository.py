from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.asset_files.models import AssetFiles
from app.shared.models.enums import FileUploadStatus


class AssetFileRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_object_key(
        self,
        object_key: str,
    ) -> AssetFiles | None:
        result = await self.session.execute(
            select(AssetFiles).where(AssetFiles.s3_object_key == object_key)
        )

        return result.scalar_one_or_none()

    async def list_expired_pending(
        self,
        *,
        cutoff: datetime,
    ) -> list[AssetFiles]:
        result = await self.session.execute(
            select(AssetFiles).where(
                AssetFiles.status == FileUploadStatus.PENDING,
                AssetFiles.created_at < cutoff,
                AssetFiles.deleted_at.is_(None),
            )
        )

        return list(result.scalars().all())

    async def get_by_id(
        self,
        file_id: UUID,
    ) -> AssetFiles | None:
        result = await self.session.execute(
            select(AssetFiles).where(AssetFiles.id == file_id)
        )

        return result.scalar_one_or_none()

    async def create(self, file: AssetFiles) -> AssetFiles:
        self.session.add(file)
        await self.session.flush()
        return file

    async def list_uploaded_for_asset(
        self,
        asset_id: UUID,
    ) -> list[AssetFiles]:
        result = await self.session.execute(
            select(AssetFiles)
            .where(
                AssetFiles.asset_id == asset_id,
                AssetFiles.status == FileUploadStatus.UPLOADED,
            )
            .order_by(AssetFiles.created_at.desc())
        )

        return list(result.scalars().all())

    async def delete(self, file: AssetFiles) -> None:
        await self.session.delete(file)
        await self.session.flush()
