from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.repositories import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session)

    async def list_users(
        self,
        *,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[list[dict], int]:

        return await self.user_repository.list_users(
            page=page,
            size=size,
            search=search,
        )
