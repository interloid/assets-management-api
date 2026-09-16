from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.asset_tag.model import AssetTagCounter
from app.models.enums import AssetType


class AssetTagCounterRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_next_number(
        self,
        company_prefix: str,
        asset_type: AssetType,
    ) -> int:
        stmt = (
            insert(AssetTagCounter)
            .values(
                company_prefix=company_prefix,
                asset_type=asset_type,
                last_number=1,
            )
            .on_conflict_do_update(
                index_elements=[
                    AssetTagCounter.company_prefix,
                    AssetTagCounter.asset_type,
                ],
                set_={
                    "last_number": (AssetTagCounter.last_number + 1),
                },
            )
            .returning(AssetTagCounter.last_number)
        )

        result = await self.session.execute(stmt)

        return result.scalar_one()
