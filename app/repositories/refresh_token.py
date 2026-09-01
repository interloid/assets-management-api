from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(
        self,
        token_hash: str,
        *,
        for_update: bool = False,
    ) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)

        if for_update:
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id,
        token_hash: str,
        family_id,
        expires_at: datetime,
    ) -> RefreshToken:

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )

        self.session.add(refresh_token)
        await self.session.flush()

        return refresh_token

    async def revoke(
        self,
        token_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)

        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.id == token_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

        await self.session.execute(stmt)

        await self.session.flush()

    async def revoke_family(
        self,
        family_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)

        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

        await self.session.execute(stmt)

        await self.session.flush()
