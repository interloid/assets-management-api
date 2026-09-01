from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DBSession = Annotated[AsyncSession, Depends(get_db)]

RefreshToken = Annotated[
    str | None,
    Cookie(alias="refresh_token"),
]
