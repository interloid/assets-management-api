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
    InvalidTokenError,
    RefreshTokenReuseError,
    UserInactiveError,
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
            raise EmailAlreadyRegisteredError()

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
            raise InvalidCredentialsError()

        if not verify_password(
            payload.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError()

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

    async def refresh(
        self,
        refresh_token: str,
    ) -> LoginResult:

        if not refresh_token:
            raise InvalidTokenError()

        token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_token_repository.get_by_hash(
            token_hash,
            for_update=True,
        )

        if stored_token is None:
            raise InvalidTokenError()

        now = datetime.now(timezone.utc)

        if stored_token.revoked_at is not None:
            await self.refresh_token_repository.revoke_family(
                stored_token.family_id,
            )

            await self.session.commit()

            raise RefreshTokenReuseError()

        if stored_token.expires_at <= now:
            await self.session.rollback()

            raise InvalidTokenError()

        user = await self.user_repository.get_by_id(
            stored_token.user_id,
        )

        if user is None:
            await self.session.rollback()

            raise InvalidTokenError()

        if not user.is_active:
            await self.session.rollback()

            raise UserInactiveError()

        family_id = stored_token.family_id

        new_refresh_token = generate_refresh_token()

        new_refresh_token_hash = hash_refresh_token(
            new_refresh_token,
        )

        new_expires_at = now + timedelta(
            days=settings.refresh_token_expiry_days,
        )

        await self.refresh_token_repository.revoke(
            stored_token.id,
        )

        await self.refresh_token_repository.create(
            user_id=user.id,
            token_hash=new_refresh_token_hash,
            family_id=family_id,
            expires_at=new_expires_at,
        )

        access_token = create_access_token(
            user_id=str(user.id),
            role=(user.role.value if hasattr(user.role, "value") else str(user.role)),
        )

        await self.session.commit()

        return LoginResult(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(
        self,
        refresh_token: str,
    ):
        if not refresh_token:
            raise InvalidTokenError()

        token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_token_repository.get_by_hash(
            token_hash,
            for_update=True,
        )

        if stored_token is None:
            raise InvalidTokenError()

        await self.refresh_token_repository.revoke(stored_token.id)

        await self.session.commit()

    async def logout_all(
        self,
        refresh_token: str,
    ):
        if not refresh_token:
            raise InvalidTokenError()

        token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_token_repository.get_by_hash(token_hash)

        if stored_token is None:
            raise InvalidTokenError()

        await self.refresh_token_repository.revoke_user(stored_token.user_id)

        await self.session.commit()

    async def change_password(
            self,
            user: User,
            current_password: str,
            new_password: str,
    ) -> None:
        if not verify_password(
            current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError

        new_password_hash = hash_password(new_password)

        await self.user_repository.update_password(
            user,
            new_password_hash,
        )

        await self.refresh_token_repository.revoke_user(
            user.id
        )

        await self.session.commit()
