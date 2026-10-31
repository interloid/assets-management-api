from datetime import datetime, timedelta, timezone
from typing import List, Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.asset.asset_assignment import AssetAssignment
from app.modules.asset.models import Asset
from app.modules.asset.tag.asset_tag_history import AssetTagHistory
from app.modules.user.models import User
from app.shared.models.enums import AssetStatus, AssetType, WarrantyExpiry
from app.shared.utils.query import escape_like

SORT_COLUMNS = {
    "created_at": Asset.created_at,
    "purchase_date": Asset.purchase_date,
    "asset_tag": Asset.asset_tag,
    "warranty_expiry": Asset.warranty_expiry,
}


def build_filters(
    *,
    asset_type: AssetType | None = None,
    asset_status: AssetStatus | None = None,
    assigned_to: UUID | None = None,
    warranty_expiry: WarrantyExpiry | None = None,
    search: str | None = None,
) -> list:
    today = datetime.now(timezone.utc).date()
    filters = [Asset.deleted_at.is_(None)]

    if asset_type is not None:
        filters.append(Asset.type == asset_type)

    if asset_status is not None:
        filters.append(Asset.status == asset_status)

    if assigned_to is not None:
        filters.append(Asset.assigned_to == assigned_to)

    if warranty_expiry == WarrantyExpiry.EXPIRES_IN_30_DAYS:
        filters.append(Asset.warranty_expiry >= today)
        filters.append(Asset.warranty_expiry <= today + timedelta(days=30))

    elif warranty_expiry == WarrantyExpiry.EXPIRES_IN_90_DAYS:
        filters.append(Asset.warranty_expiry >= today)
        filters.append(Asset.warranty_expiry <= today + timedelta(days=90))

    elif warranty_expiry == WarrantyExpiry.ALREADY_EXPIRED:
        filters.append(Asset.warranty_expiry < today)

    if search:
        search_pattern = f"%{escape_like(search.strip())}%"
        filters.append(
            or_(
                Asset.asset_tag.ilike(search_pattern, escape="\\"),
                Asset.serial_number.ilike(search_pattern, escape="\\"),
                Asset.notes.ilike(search_pattern, escape="\\"),
            )
        )

    return filters


def build_ordering(
    *,
    sort: Literal[
        "created_at", "purchase_date", "warranty_expiry", "asset_tag"
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> list:
    sort_column = SORT_COLUMNS[sort]

    if sort == "warranty_expiry":
        order_by_clause = (
            sort_column.asc().nullslast()
            if order == "asc"
            else sort_column.desc().nullslast()
        )
    else:
        order_by_clause = sort_column.asc() if order == "asc" else sort_column.desc()

    if sort == "created_at":
        return [order_by_clause, Asset.id.asc()]

    return [
        order_by_clause,
        Asset.created_at.desc(),
        Asset.id.asc(),
    ]


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset

    async def add_history(
        self,
        asset_history: AssetAssignment,
    ) -> AssetAssignment:
        self.session.add(asset_history)
        await self.session.flush()
        await self.session.refresh(asset_history)
        return asset_history

    async def list_for_export(
        self,
        *,
        asset_type: AssetType | None = None,
        asset_status: AssetStatus | None = None,
        assigned_to: UUID | None = None,
        warranty_expiry: WarrantyExpiry | None = None,
        search: str | None = None,
        sort: Literal[
            "created_at", "purchase_date", "warranty_expiry", "asset_tag"
        ] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> list[Asset]:
        filters = build_filters(
            asset_type=asset_type,
            asset_status=asset_status,
            assigned_to=assigned_to,
            warranty_expiry=warranty_expiry,
            search=search,
        )

        order_clauses = build_ordering(
            sort=sort,
            order=order,
        )

        query = (
            select(Asset)
            .options(selectinload(Asset.assigned_user))
            .where(*filters)
            .order_by(*order_clauses)
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def list_assets(
        self,
        *,
        page: int,
        size: int,
        asset_type: AssetType | None = None,
        asset_status: AssetStatus | None = None,
        assigned_to: UUID | None = None,
        warranty_expiry: WarrantyExpiry | None = None,
        search: str | None = None,
        sort: Literal[
            "created_at", "purchase_date", "warranty_expiry", "asset_tag"
        ] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[Asset], int]:

        filters = build_filters(
            asset_type=asset_type,
            asset_status=asset_status,
            assigned_to=assigned_to,
            warranty_expiry=warranty_expiry,
            search=search,
        )

        order_clauses = build_ordering(sort=sort, order=order)

        offset = (page - 1) * size
        query = (
            select(Asset, func.count().over().label("total_count"))
            .options(selectinload(Asset.assigned_user))
            .where(*filters)
            .order_by(*order_clauses)
            .offset(offset)
            .limit(size)
        )
        result = await self.session.execute(query)
        rows = result.all()

        if not rows:
            count_query = select(func.count()).select_from(Asset).where(*filters)
            total = (await self.session.execute(count_query)).scalar_one()
            return [], total

        assets = [row[0] for row in rows]
        total = rows[0].total_count

        return assets, total

    async def get_by_id(
        self,
        asset_id: UUID,
    ) -> Asset | None:
        stmt = (
            select(Asset)
            .options(selectinload(Asset.assigned_user))
            .where(Asset.id == asset_id, Asset.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_id_including_deleted(
        self,
        asset_id: UUID,
    ) -> Asset | None:
        stmt = (
            select(Asset)
            .options(selectinload(Asset.assigned_user))
            .where(Asset.id == asset_id)
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def update(
        self,
        asset: Asset,
        update_data: dict,
    ) -> Asset:
        for field, value in update_data.items():
            setattr(asset, field, value)

        await self.session.flush()
        await self.session.refresh(asset)

        return asset

    async def delete(
        self,
        asset: Asset,
    ) -> None:
        if asset.deleted_at is not None:
            return
        asset.deleted_at = datetime.now(timezone.utc)
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

    async def change_status(
        self,
        *,
        asset: Asset,
        new_status: AssetStatus,
    ) -> Asset:
        asset.status = new_status

        if new_status == AssetStatus.REPAIR:
            asset.assigned_to = None

        await self.session.flush()
        await self.session.refresh(asset)

        return asset

    async def stats(self) -> dict[AssetStatus, int]:
        stmt = (
            select(
                Asset.status,
                func.count(Asset.id).label("count"),
            )
            .where(Asset.deleted_at.is_(None))
            .group_by(Asset.status)
        )

        result = await self.session.execute(stmt)

        return dict(result.all())

    async def get_history_by_asset_id(
        self,
        asset_id: UUID,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[list[AssetAssignment], int]:
        filters = [AssetAssignment.asset_id == asset_id]

        if search and (term := search.strip()):
            pattern = f"%{escape_like(term)}%"
            filters.append(
                or_(
                    User.full_name.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = (
            select(func.count(AssetAssignment.id))
            .join(User, AssetAssignment.user_id == User.id)
            .where(*filters)
        )
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            select(AssetAssignment)
            .join(User, AssetAssignment.user_id == User.id)
            .where(*filters)
            .options(
                selectinload(AssetAssignment.user),
                selectinload(AssetAssignment.assigner),
                selectinload(AssetAssignment.un_assigner),
            )
            .order_by(
                AssetAssignment.assigned_at.asc(),
                AssetAssignment.id.asc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_active_assignment_by_id(
        self,
        asset_id: UUID,
    ) -> AssetAssignment | None:
        stmt = select(AssetAssignment).where(
            AssetAssignment.asset_id == asset_id,
            AssetAssignment.returned_at.is_(None),
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history_by_user_id(
        self,
        user_id: UUID,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[List[AssetAssignment], int]:
        filters = [AssetAssignment.user_id == user_id]

        if search and (term := search.strip()):
            pattern = f"%{escape_like(term)}%"
            filters.append(
                or_(
                    Asset.asset_tag.ilike(pattern, escape="\\"),
                    Asset.serial_number.ilike(pattern, escape="\\"),
                    Asset.notes.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = (
            select(func.count(AssetAssignment.id))
            .join(Asset, AssetAssignment.asset_id == Asset.id)
            .where(*filters)
        )
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            select(AssetAssignment)
            .join(Asset, AssetAssignment.asset_id == Asset.id)
            .where(*filters)
            .options(
                selectinload(AssetAssignment.asset),
                selectinload(AssetAssignment.assigner),
                selectinload(AssetAssignment.un_assigner),
            )
            .order_by(
                AssetAssignment.assigned_at.desc(),
                AssetAssignment.id.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_tag_history(
        self,
        asset_id: UUID,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[list[AssetTagHistory], int]:
        filters = [AssetTagHistory.asset_id == asset_id]

        if search and (term := search.strip()):
            pattern = f"%{escape_like(term)}%"
            filters.append(
                or_(
                    AssetTagHistory.old_asset_tag.ilike(
                        pattern,
                        escape="\\",
                    ),
                    AssetTagHistory.new_asset_tag.ilike(
                        pattern,
                        escape="\\",
                    ),
                )
            )

        count_stmt = select(func.count(AssetTagHistory.id)).where(*filters)
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            select(AssetTagHistory)
            .where(*filters)
            .options(selectinload(AssetTagHistory.changed_by_user))
            .order_by(
                AssetTagHistory.changed_at.desc(),
                AssetTagHistory.id.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all(), total
