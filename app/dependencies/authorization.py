from fastapi import Depends

from app.dependencies.authentication import get_current_user
from app.exceptions.authorization import AuthorizationError
from app.models.user import User
from app.schemas.auth import UserRole


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError()

    return current_user
