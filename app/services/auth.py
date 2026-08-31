from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.exceptions.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResult,
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

    async def login(
        self,
        payload: LoginRequest,
    ) -> LoginResult:
        user = await self.user_repository.get_by_email(payload.email)

        if user is None:
            raise InvalidCredentialsError

        if not verify_password(
            payload.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InvalidCredentialsError

        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
        )

        refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expiry_days
        )

        family_id = uuid7()

        await self.refresh_token_repository.create(
            user_id=user.id,
            token_hash=refresh_token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )

        await self.session.commit()

        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
        )
