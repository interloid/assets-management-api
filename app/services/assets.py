import re
from datetime import date
from math import ceil
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.asset_tag.generator import build_asset_tag, get_company_prefix
from app.asset_tag.repository import AssetTagCounterRepository
from app.exceptions.assets import (
    AssetNotFoundError,
    AssetTagAlreadyExistsError,
    SerialNumberAlreadyExistsError,
)
from app.models.assets import Asset
from app.models.enums import AssetStatus, AssetType, UserRole
from app.models.user import User
from app.repositories.assets import AssetRepository
from app.schemas.assets import AssetCreate, AssetListResponse, AssetResponse


def get_constraint_name(exc: IntegrityError) -> str | None:
    message = str(exc.orig)

    match = re.search(
        r'violates unique constraint "([^"]+)"',
        message,
    )

    if match:
        return match.group(1)

    return None


class AssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.asset_repository = AssetRepository(session)
        self.asset_tag_counter_repository = AssetTagCounterRepository(session)

    async def create(self, data: AssetCreate) -> Asset:
        company_prefix = get_company_prefix()

        number = await self.asset_tag_counter_repository.get_next_number(
            company_prefix=company_prefix,
            asset_type=data.type,
        )

        asset_tag = build_asset_tag(
            asset_type=data.type,
            number=number,
        )

        asset = Asset(
            asset_tag=asset_tag,
            type=data.type,
            serial_number=data.serial_number,
            status=AssetStatus.IN_STOCK,
            assigned_to=None,
            purchase_date=data.purchase_date,
            warranty_expiry=data.warranty_expiry,
            notes=data.notes,
        )

        try:
            await self.asset_repository.create(asset)
            await self.session.commit()

        except IntegrityError as exc:
            await self.session.rollback()

            constraint_name = get_constraint_name(exc)

            if constraint_name == "assets_serial_number_key":
                raise SerialNumberAlreadyExistsError() from exc

            if constraint_name == "assets_asset_tag_key":
                raise AssetTagAlreadyExistsError() from exc

            raise

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
    ) -> AssetListResponse:
        assets, total = await self.asset_repository.list(
            page=page,
            size=size,
            asset_type=asset_type,
            asset_status=asset_status,
            assigned_to=assigned_to,
            warranty_expiring_before=warranty_expiring_before,
            search=search,
        )

        pages = ceil(total / size) if total else 0

        return AssetListResponse(
            items=[AssetResponse.model_validate(asset) for asset in assets],
            page=page,
            size=size,
            total=total,
            pages=pages,
        )

    async def get_by_id(
        self,
        *,
        asset_id: UUID,
        current_user: User,
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        if current_user.role == UserRole.ADMIN:
            return asset

        if asset.assigned_to == current_user.id:
            return asset

        raise AssetNotFoundError()
