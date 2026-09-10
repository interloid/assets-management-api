import re
from datetime import date
from math import ceil
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.asset_tag.generator import build_asset_tag, get_company_prefix
from app.asset_tag.repository import AssetTagCounterRepository
from app.exceptions.assets import (
    AssetAssignmentUserInactiveError,
    AssetAssignmentUserNotFoundError,
    AssetDeleteConflictError,
    AssetNotFoundError,
    AssetTagAlreadyExistsError,
    InvalidAssetStatusTransitionError,
    SerialNumberAlreadyExistsError,
)
from app.models.assets import Asset
from app.models.enums import AssetStatus, AssetType, UserRole
from app.models.user import User
from app.repositories.assets import AssetRepository
from app.repositories.user import UserRepository
from app.schemas.assets import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
)

ALLOWED_STATUS_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    AssetStatus.IN_STOCK: {
        AssetStatus.ASSIGNED,
        AssetStatus.REPAIR,
        AssetStatus.RETIRED,
    },
    AssetStatus.ASSIGNED: {
        AssetStatus.IN_STOCK,
        AssetStatus.REPAIR,
    },
    AssetStatus.REPAIR: {
        AssetStatus.IN_STOCK,
        AssetStatus.RETIRED,
    },
    AssetStatus.RETIRED: set(),
}


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
        self.user_repository = UserRepository(session)

    def _validate_status_transition(
        self,
        current_status: AssetStatus,
        new_status: AssetStatus,
    ) -> None:
        allowed = ALLOWED_STATUS_TRANSITIONS[current_status]

        if new_status not in allowed:
            raise InvalidAssetStatusTransitionError(
                current_status=current_status.value,
                new_status=new_status.value,
            )

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

    async def update(
        self,
        asset_id: UUID,
        data: AssetUpdate,
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        try:
            update_data = data.model_dump(exclude_unset=True)

            if "type" in update_data:
                new_type = update_data["type"]

                if new_type != asset.type:
                    company_prefix = get_company_prefix()

                    number = await self.asset_tag_counter_repository.get_next_number(
                        company_prefix=company_prefix,
                        asset_type=new_type,
                    )

                    print("NEXT NUMBER:", number)

                    asset.asset_tag = build_asset_tag(
                        asset_type=new_type,
                        number=number,
                    )

                    print("NEW TAG:", asset.asset_tag)

            await self.asset_repository.update(
                asset=asset,
                data=data,
            )

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

    async def delete(self, asset_id: UUID) -> None:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        if asset.status not in {
            AssetStatus.IN_STOCK,
            AssetStatus.RETIRED,
        }:
            raise AssetDeleteConflictError()

        await self.asset_repository.delete(asset)

    async def assign(
        self,
        asset_id: UUID,
        user_id: UUID,
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=AssetStatus.ASSIGNED,
        )

        user = await self.user_repository.get_by_id(user_id)

        if user is None:
            raise AssetAssignmentUserNotFoundError()

        if not user.is_active:
            raise AssetAssignmentUserInactiveError()

        await self.asset_repository.assign(
            asset,
            user_id,
        )

        await self.session.commit()

        return asset

    async def unassign(self, asset_id: UUID) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=AssetStatus.IN_STOCK,
        )

        await self.asset_repository.unassign(asset)

        await self.session.commit()

        return asset
