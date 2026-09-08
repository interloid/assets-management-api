from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assets import Asset


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset
