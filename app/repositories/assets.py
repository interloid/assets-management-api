from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assets import Asset
from app.models.enums import AssetStatus, AssetType
from app.schemas.assets import AssetUpdate


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset

    async def list(
        self,
        *,
        page: int,
        size: int,
        asset_type: AssetType | None = None,
        asset_status: AssetStatus | None = None,
        assigned_to: UUID | None = None,
        warranty_expiring_before: date | None = None,
        search: str | None = None,
    ) -> tuple[list[Asset], int]:
        filters = []

        if asset_type is not None:
            filters.append(Asset.type == asset_type)

        if asset_status is not None:
            filters.append(Asset.status == asset_status)

        if assigned_to is not None:
            filters.append(Asset.assigned_to == assigned_to)

        if warranty_expiring_before is not None:
            filters.append(Asset.warranty_expiry <= warranty_expiring_before)

        if search:
            search = search.strip()
            search_pattern = f"%{escape_like(search)}%"

            filters.append(
                or_(
                    Asset.asset_tag.ilike(
                        search_pattern,
                        escape="\\",
                    ),
                    Asset.serial_number.ilike(
                        search_pattern,
                        escape="\\",
                    ),
                    Asset.notes.ilike(
                        search_pattern,
                        escape="\\",
                    ),
                ),
            )

        total_query = select(func.count()).select_from(Asset).where(*filters)

        total_result = await self.session.execute(total_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size

        query = (
            select(Asset)
            .where(*filters)
            .order_by(Asset.created_at.desc())
            .offset(offset)
            .limit(size)
        )

        result = await self.session.execute(query)

        assets = list(result.scalars().all())

        return assets, total

    async def get_by_id(
        self,
        asset_id: UUID,
    ) -> Asset:
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def update(
        self,
        asset: Asset,
        data: AssetUpdate,
    ) -> Asset:
        updated_data = data.model_dump(exclude_unset=True)

        for field, value in updated_data.items():
            setattr(asset, field, value)

        await self.session.flush()
        await self.session.refresh(asset)

        return asset

    async def delete(
        self,
        asset: Asset,
    ) -> None:
        await self.session.delete(asset)
        await self.session.flush()

    async def assign(
        self,
        asset: Asset,
        user_id: UUID,
    ) -> Asset:
        asset.status = AssetStatus.ASSIGNED
        asset.assigned_to = user_id

        await self.session.flush()
        await self.session.refresh(asset)

        return asset

    async def unassign(
        self,
        asset: Asset,
    ) -> Asset:
        asset.assigned_to = None
        asset.status = AssetStatus.IN_STOCK

        await self.session.flush()
        await self.session.refresh(asset)

        return asset
