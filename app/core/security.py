import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from uuid6 import uuid7

from app.core.config import settings
from app.exceptions.auth import InvalidTokenError

password_hash = PasswordHash.recommended()


TIMING_HASH = "$argon2id$v=19$m=65536,t=3,p=4$91VoC3BeweKJ+9VtlmV6fg$+Na3rOKaPG06lZZsQBNTHhA0YPMBm/WwRLm655fxaC0"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(
    *,
    user_id: str,
    role: str,
    token_version: int,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expiry_minutes)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid7()),
        "token_version": token_version,
    }

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": [
                    "sub",
                    "role",
                    "iat",
                    "exp",
                    "jti",
                    "token_version",
                ],
            },
        )

    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError() from exc

    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc

    return payload


def get_token_remaining_seconds(exp: int | float) -> int:
    now = datetime.now(timezone.utc).timestamp()

    return max(
        0,
        int(exp - now),
    )
