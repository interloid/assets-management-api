import json
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RedisClient
from app.modules.asset.asset_assignment import AssetAssignment
from app.modules.asset.exceptions import (
    AssetAssignmentUserInactiveError,
    AssetAssignmentUserNotFoundError,
    AssetDeleteConflictError,
    AssetHistoryNotFoundError,
    AssetNotFoundError,
    AssetTagAlreadyExistsError,
    InvalidAssetStatusTransitionError,
    InvalidWarrantyExpiryError,
    SerialNumberAlreadyExistsError,
)
from app.modules.asset.models import Asset
from app.modules.asset.repositories import AssetRepository
from app.modules.asset.tag.generator import build_asset_tag, get_company_prefix
from app.modules.asset.tag.repository import AssetTagCounterRepository
from app.modules.auth.exceptions import AuthorizationError
from app.modules.user.models import User
from app.modules.user.repositories import UserRepository
from app.shared.models.enums import AssetStatus, AssetType, UserRole

ASSET_STATS_CACHE_KEY = "assets:stats"
ASSET_STATS_CACHE_TTL = 60
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
    cause = getattr(exc.orig, "__cause__", None)

    if cause is None:
        return None

    return getattr(cause, "constraint_name", None)


class AssetService:
    def __init__(self, session: AsyncSession, redis_client: RedisClient) -> None:
        self.session = session
        self.asset_repository = AssetRepository(session)
        self.asset_tag_counter_repository = AssetTagCounterRepository(session)
        self.user_repository = UserRepository(session)
        self.redis_client = redis_client

    def validate_warranty_expiry(
        self,
        *,
        purchase_date: date,
        warranty_expiry: date | None,
    ) -> None:
        if warranty_expiry is not None and warranty_expiry < purchase_date:
            raise InvalidWarrantyExpiryError()

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

    async def create(
        self,
        *,
        asset_type: AssetType,
        serial_number: str,
        purchase_date: date,
        warranty_expiry: date | None,
        notes: str | None,
    ) -> Asset:
        self.validate_warranty_expiry(
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
        )

        company_prefix = get_company_prefix()

        number = await self.asset_tag_counter_repository.get_next_number(
            company_prefix=company_prefix,
            asset_type=asset_type,
        )

        asset_tag = build_asset_tag(
            asset_type=asset_type,
            number=number,
        )

        asset = Asset(
            asset_tag=asset_tag,
            type=asset_type,
            serial_number=serial_number,
            status=AssetStatus.IN_STOCK,
            assigned_to=None,
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
            notes=notes,
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

        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)
        return asset

    async def list(
        self,
        *,
        page: int,
        size: int,
        asset_type: AssetType | None = None,
        asset_status: AssetStatus | None = None,
        assigned_to: UUID | None = None,
        warranty_expiry: date | None = None,
        search: str | None = None,
        sort: Literal[
            "created_at", "purchase_date", "warranty_expiry", "asset_tag"
        ] = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[Asset], int]:
        assets, total = await self.asset_repository.list(
            page=page,
            size=size,
            asset_type=asset_type,
            asset_status=asset_status,
            assigned_to=assigned_to,
            warranty_expiry=warranty_expiry,
            search=search,
            sort=sort,
            order=order,
        )

        return assets, total

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

        raise AuthorizationError()

    async def update(
        self,
        asset_id: UUID,
        update_data: dict,
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        purchase_date = update_data.get(
            "purchase_date",
            asset.purchase_date,
        )
        warranty_expiry = update_data.get(
            "warranty_expiry",
            asset.warranty_expiry,
        )

        self.validate_warranty_expiry(
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
        )

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

        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)
        return asset

    async def delete(self, asset_id: UUID) -> None:
        asset = await self.asset_repository.get_by_id_including_deleted(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        if asset.deleted_at is not None:
            return

        if asset.status not in {
            AssetStatus.IN_STOCK,
            AssetStatus.RETIRED,
        }:
            raise AssetDeleteConflictError()

        await self.asset_repository.delete(asset)

        await self.session.commit()
        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)

    async def assign(self, asset_id: UUID, user_id: UUID, assigned_by: UUID) -> Asset:
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

        asset_history = AssetAssignment(
            asset_id=asset_id,
            user_id=user_id,
            assigned_by=assigned_by,
            unassigned_by=None,
            assigned_at=datetime.now(UTC),
            returned_at=None,
        )
        await self.asset_repository.assign(asset, user_id)
        await self.asset_repository.add_history(asset_history)
        await self.session.commit()
        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)

        return asset

    async def unassign(self, asset_id: UUID, unassigned_by: UUID) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=AssetStatus.IN_STOCK,
            allowed_map=ALLOWED_STATUS_TRANSITIONS,
        )

        asset_history = await self.asset_repository.get_active_assignment_by_id(
            asset_id
        )

        if asset_history is None:
            raise AssetHistoryNotFoundError()

        asset_history.unassigned_by = unassigned_by
        asset_history.returned_at = datetime.now(UTC)

        await self.asset_repository.unassign(asset)
        await self.session.commit()
        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)

        return asset

    async def change_status(
        self, asset_id: UUID, new_status: AssetStatus, changed_by: UUID
    ) -> Asset:
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        self._validate_status_transition(
            current_status=asset.status,
            new_status=new_status,
            allowed_map=MANUAL_STATUS_TRANSITIONS,
        )

        if asset.status == AssetStatus.ASSIGNED and new_status == AssetStatus.REPAIR:
            asset_history = await self.asset_repository.get_active_assignment_by_id(
                asset_id
            )

            if asset_history is None:
                raise AssetHistoryNotFoundError()

            asset_history.returned_at = datetime.now(UTC)
            asset_history.unassigned_by = changed_by

        await self.asset_repository.change_status(
            asset=asset,
            new_status=new_status,
        )

        await self.session.commit()
        await self.redis_client.delete(ASSET_STATS_CACHE_KEY)

        return asset

    async def stats(self) -> dict[str, int]:
        cached = await self.redis_client.get(ASSET_STATS_CACHE_KEY)

        if cached is not None:
            return json.loads(cached)

        counts = await self.asset_repository.stats()

        in_stock = counts.get(AssetStatus.IN_STOCK, 0)
        assigned = counts.get(AssetStatus.ASSIGNED, 0)
        repair = counts.get(AssetStatus.REPAIR, 0)
        retired = counts.get(AssetStatus.RETIRED, 0)

        result = {
            "total": in_stock + assigned + repair + retired,
            "in_stock": in_stock,
            "assigned": assigned,
            "repair": repair,
            "retired": retired,
        }

        await self.redis_client.set(
            ASSET_STATS_CACHE_KEY,
            json.dumps(result),
            ex=ASSET_STATS_CACHE_TTL,
        )

        return result

    async def get_history_by_asset(
        self,
        asset_id: UUID,
    ):
        asset = await self.asset_repository.get_by_id(asset_id)

        if asset is None:
            raise AssetNotFoundError()

        asset_history = await self.asset_repository.get_history_by_asset_id(asset_id)

        if asset_history is None:
            raise AssetHistoryNotFoundError()

        return asset_id, asset_history

    async def get_history_by_user(
        self,
        user_id: UUID,
        current_user: User,
    ):
        user = await self.user_repository.get_by_id(user_id=user_id)

        if user is None:
            raise AssetAssignmentUserNotFoundError()
        user_history = await self.asset_repository.get_history_by_user_id(
            user_id=user_id
        )

        if current_user.role == UserRole.ADMIN:
            return user_history

        if current_user.id == user_id:
            return user_history

        raise AuthorizationError()
