import re
from datetime import date
from math import ceil
from typing import Literal
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

ASSIGNMENT_ONLY_TRANSITIONS: set[tuple[AssetStatus, AssetStatus]] = {
    (AssetStatus.IN_STOCK, AssetStatus.ASSIGNED),
    (AssetStatus.ASSIGNED, AssetStatus.IN_STOCK),
}

MANUAL_STATUS_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    current: {
        target
        for target in targets
        if (current, target) not in ASSIGNMENT_ONLY_TRANSITIONS
    }
    for current, targets in ALLOWED_STATUS_TRANSITIONS.items()
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
        *,
        current_status: AssetStatus,
        new_status: AssetStatus,
        allowed_map: dict[AssetStatus, set[AssetStatus]],
    ) -> None:
        allowed = allowed_map[current_status]

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
        sort: Literal["created_at", "purchase_date", "asset_tag"] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> AssetListResponse:
        assets, total = await self.asset_repository.list(
            page=page,
            size=size,
            asset_type=asset_type,
            asset_status=asset_status,
            assigned_to=assigned_to,
            warranty_expiring_before=warranty_expiring_before,
            search=search,
            sort=sort,
            order=order,
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

        update_data = data.model_dump(exclude_unset=True)

        try:
            if "type" in update_data:
                new_type = update_data["type"]

                if new_type != asset.type:
                    company_prefix = get_company_prefix()

                    number = await self.asset_tag_counter_repository.get_next_number(
                        company_prefix=company_prefix,
                        asset_type=new_type,
                    )

                    update_data["asset_tag"] = build_asset_tag(
                        asset_type=new_type,
                        number=number,
                    )

            await self.asset_repository.update(
                asset=asset,
                update_data=update_data,
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

        await self.session.commit()

    async def assign(self, asset_id: UUID, user_id: UUID) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=AssetStatus.ASSIGNED,
            allowed_map=ALLOWED_STATUS_TRANSITIONS,
        )

        user = await self.user_repository.get_by_id(user_id)

        if user is None:
            raise AssetAssignmentUserNotFoundError()

        if not user.is_active:
            raise AssetAssignmentUserInactiveError()

        await self.asset_repository.assign(asset, user_id)
        await self.session.commit()

        return asset

    async def unassign(self, asset_id: UUID) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=AssetStatus.IN_STOCK,
            allowed_map=ALLOWED_STATUS_TRANSITIONS,
        )

        await self.asset_repository.unassign(asset)
        await self.session.commit()

        return asset

    async def change_status(
        self,
        asset_id: UUID,
        new_status: AssetStatus,
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=new_status,
            allowed_map=MANUAL_STATUS_TRANSITIONS,
        )

        await self.asset_repository.change_status(asset=asset, new_status=new_status)
        await self.session.commit()

        return asset

    async def summary(self) -> dict[str, int]:
        counts = await self.asset_repository.summary()

        in_stock = counts.get(AssetStatus.IN_STOCK, 0)
        assigned = counts.get(AssetStatus.ASSIGNED, 0)
        repair = counts.get(AssetStatus.REPAIR, 0)
        retired = counts.get(AssetStatus.RETIRED, 0)

        return {
            "total": in_stock + assigned + repair + retired,
            "in_stock": in_stock,
            "assigned": assigned,
            "repair": repair,
            "retired": retired,
        }
