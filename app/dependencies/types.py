from typing import Annotated, Any

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.authentication import (
    get_current_access_token,
    get_current_user,
    get_logout_access_token,
    get_logout_all_context,
)
from app.dependencies.authorization import require_admin
from app.models.user import User

DBSession = Annotated[AsyncSession, Depends(get_db)]

RefreshToken = Annotated[
    str | None,
    Cookie(alias="refresh_token"),
]

CurrentUser = Annotated[User, Depends(get_current_user)]

AdminUser = Annotated[User, Depends(require_admin)]

AccessTokenPayload = Annotated[
    dict[str, Any],
    Depends(get_current_access_token),
]

LogoutAccessTokenPayload = Annotated[
    dict[str, Any],
    Depends(get_logout_access_token),
]

LogoutAllContext = Annotated[
    dict[str, Any],
    Depends(get_logout_all_context),
]
