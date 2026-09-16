from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import escape_like
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))

        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash

        await self.session.flush()

        return user

    async def increment_token_version(self, user: User) -> None:
        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(
                token_version=User.token_version + 1,
                updated_at=func.now(),
            )
            .returning(User.token_version)
        )

        result = await self.session.execute(stmt)

        user.token_version = result.scalar_one()

    async def list_users(
        self,
        *,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        filters = []
        if search:
            search = search.strip()
            search_pattern = f"%{escape_like(search)}%"

            filters.append(
                or_(
                    User.email.ilike(search_pattern, escape="\\"),
                    User.full_name.ilike(search_pattern, escape="\\"),
                ),
            )

        offset = (page - 1) * size

        stmt = (
            select(
                User,
                func.count().over().label("total_count"),
            )
            .where(*filters)
            .order_by(User.created_at.desc(), User.id.asc())
            .offset(offset)
            .limit(size)
        )

        result = await self.session.execute(stmt)

        rows = result.all()

        if not rows:
            count_query = select(func.count()).select_from(User).where(*filters)

            total = (await self.session.execute(count_query)).scalar_one()

            return [], total

        users = [row[0] for row in rows]
        total = rows[0].total_count

        return users, total
