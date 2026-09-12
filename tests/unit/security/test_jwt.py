from datetime import datetime, timedelta, timezone

import jwt
from uuid6 import uuid7

from app.core.config import settings
from app.core.security import create_access_token


def test_jwt_contains_required_claims() -> None:
    user_id = str(uuid7())

    token = create_access_token(
        user_id=user_id,
        role="user",
        token_version=0,
    )

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload["sub"] == user_id
    assert payload["role"] == "user"
    assert payload["token_version"] == 0
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload


def test_jwt_expires_after_15_minutes() -> None:
    user_id = str(uuid7())

    token = create_access_token(
        user_id=user_id,
        role="user",
        token_version=0,
    )

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

    assert expires_at - issued_at == timedelta(minutes=15)


def test_each_jwt_has_unique_jti() -> None:
    user_id = str(uuid7())

    token_1 = create_access_token(
        user_id=user_id,
        role="user",
        token_version=0,
    )

    token_2 = create_access_token(
        user_id=user_id,
        role="user",
        token_version=0,
    )

    payload_1 = jwt.decode(
        token_1,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    payload_2 = jwt.decode(
        token_2,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload_1["jti"] != payload_2["jti"]
