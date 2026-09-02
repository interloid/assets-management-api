from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

DBSession = Annotated[AsyncSession, Depends(get_db)]

RefreshToken = Annotated[
    str | None,
    Cookie(alias="refresh_token"),
]

CurrentUser = Annotated[User, Depends(get_current_user)]
