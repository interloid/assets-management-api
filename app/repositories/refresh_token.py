from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
