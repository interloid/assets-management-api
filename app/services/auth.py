from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
)
from app.exceptions.auth import (
    EmailAlreadyRegisteredError,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    RegisterRequest,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> User:
        existing_user = await self.user_repository.get_by_email(str(data.email))

        if existing_user is not None:
            raise EmailAlreadyRegisteredError

        password_hash = hash_password(data.password)

        try:
            user = await self.user_repository.create(
                email=str(data.email),
                password_hash=password_hash,
                full_name=data.full_name,
            )

            await self.session.commit()

        except IntegrityError as exc:
            await self.session.rollback()

            raise EmailAlreadyRegisteredError from exc

        return user


