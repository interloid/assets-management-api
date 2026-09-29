from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from uuid6 import uuid7

from app.api.v1.dependencies import get_current_user
from app.core.security import TIMING_HASH
from app.modules.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenReuseError,
    SamePasswordError,
)


@pytest.mark.asyncio
async def test_valid_credentials(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=active_user,
    )

    auth_service.refresh_token_repository.create = AsyncMock()

    with (
        patch(
            "app.modules.auth.services.verify_password",
            return_value=True,
        ) as mock_verify_password,
        patch(
            "app.modules.auth.services.create_access_token",
            return_value="access-token",
        ) as mock_create_access_token,
        patch(
            "app.modules.auth.services.generate_refresh_token",
            return_value="refresh-token",
        ) as mock_generate_refresh_token,
        patch(
            "app.modules.auth.services.hash_refresh_token",
            return_value="refresh-token-hash",
        ) as mock_hash_refresh_token,
    ):
        result = await auth_service.login(
            login_payload,
        )

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        login_payload.email,
    )

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        active_user.password_hash,
    )

    mock_create_access_token.assert_called_once_with(
        user_id=str(active_user.id),
        role=active_user.role.value,
        token_version=active_user.token_version,
    )

    mock_generate_refresh_token.assert_called_once()

    mock_hash_refresh_token.assert_called_once_with(
        "refresh-token",
    )

    auth_service.refresh_token_repository.create.assert_awaited_once()

    mock_session.commit.assert_awaited_once()

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"


@pytest.mark.asyncio
async def test_unknown_email(
    auth_service,
    mock_session,
    login_payload,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=None,
    )

    with (
        patch(
            "app.modules.auth.services.verify_password",
        ) as mock_verify_password,
        patch(
            "app.modules.auth.services.create_access_token",
        ) as mock_create_access_token,
        patch(
            "app.modules.auth.services.generate_refresh_token",
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                login_payload,
            )

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        login_payload.email,
    )

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        TIMING_HASH,
    )

    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_incorrect_password(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=active_user,
    )

    with (
        patch(
            "app.modules.auth.services.verify_password",
            return_value=False,
        ) as mock_verify_password,
        patch(
            "app.modules.auth.services.create_access_token",
        ) as mock_create_access_token,
        patch(
            "app.modules.auth.services.generate_refresh_token",
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                login_payload,
            )

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        active_user.password_hash,
    )

    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_user(
    auth_service,
    mock_session,
    login_payload,
    inactive_user,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=inactive_user,
    )

    with (
        patch(
            "app.modules.auth.services.verify_password",
            return_value=True,
        ) as mock_verify_password,
        patch(
            "app.modules.auth.services.create_access_token",
        ) as mock_create_access_token,
        patch(
            "app.modules.auth.services.generate_refresh_token",
        ) as mock_generate_refresh_token,
    ):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                login_payload,
            )

    mock_verify_password.assert_called_once_with(
        login_payload.password,
        inactive_user.password_hash,
    )

    mock_create_access_token.assert_not_called()
    mock_generate_refresh_token.assert_not_called()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_token_created(
    auth_service,
    mock_session,
    login_payload,
    active_user,
) -> None:

    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=active_user,
    )

    auth_service.refresh_token_repository.create = AsyncMock()

    with (
        patch(
            "app.modules.auth.services.verify_password",
            return_value=True,
        ),
        patch(
            "app.modules.auth.services.create_access_token",
            return_value="access-token",
        ),
        patch(
            "app.modules.auth.services.generate_refresh_token",
            return_value="refresh-token",
        ) as mock_generate_refresh_token,
        patch(
            "app.modules.auth.services.hash_refresh_token",
            return_value="hashed-refresh-token",
        ) as mock_hash_refresh_token,
    ):
        result = await auth_service.login(
            login_payload,
        )

    mock_generate_refresh_token.assert_called_once()

    mock_hash_refresh_token.assert_called_once_with(
        "refresh-token",
    )

    auth_service.refresh_token_repository.create.assert_awaited_once()

    create_kwargs = auth_service.refresh_token_repository.create.await_args.kwargs

    assert create_kwargs["user_id"] == active_user.id
    assert create_kwargs["token_hash"] == "hashed-refresh-token"
    assert create_kwargs["family_id"] is not None
    assert create_kwargs["expires_at"] is not None

    mock_session.commit.assert_awaited_once()

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"


@pytest.mark.asyncio
async def test_valid_logout(
    auth_service,
    mock_session,
    created_refresh_token,
) -> None:
    mock_redis = AsyncMock()
    refresh_token = "valid refresh token"

    access_token_payload = {
        "jti": "jti-123",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 900,
    }

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            return_value="hashed_refresh_token",
        ) as mock_hash,
        patch(
            "app.modules.auth.services.blacklist_access_token",
            new_callable=AsyncMock,
        ) as mock_blacklist,
    ):
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=created_refresh_token,
        )

        auth_service.refresh_token_repository.revoke = AsyncMock()

        await auth_service.logout(
            refresh_token,
            access_token_payload,
            mock_redis,
        )

    mock_hash.assert_called_once_with(refresh_token)

    auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "hashed_refresh_token",
    )

    auth_service.refresh_token_repository.revoke.assert_awaited_once_with(
        created_refresh_token.id,
    )

    mock_blacklist.assert_awaited_once()

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_empty_refresh_token(
    auth_service,
    mock_session,
) -> None:
    mock_redis = AsyncMock()

    access_token_payload = {
        "jti": "jti-123",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 900,
    }

    with patch(
        "app.modules.auth.services.blacklist_access_token",
        new_callable=AsyncMock,
    ) as mock_blacklist:
        await auth_service.logout(
            None,
            access_token_payload,
            mock_redis,
        )

    mock_blacklist.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_refresh_token_not_found(
    auth_service,
    mock_session,
) -> None:
    mock_redis = AsyncMock()

    refresh_token = "invalid_refresh_token"

    access_token_payload = {
        "jti": "jti-123",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 900,
    }

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            return_value="hashed_refresh_token",
        ) as mock_hash,
        patch(
            "app.modules.auth.services.blacklist_access_token",
            new_callable=AsyncMock,
        ) as mock_blacklist,
    ):
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=None,
        )

        await auth_service.logout(
            refresh_token,
            access_token_payload,
            mock_redis,
        )

    mock_hash.assert_called_once_with(refresh_token)

    auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "hashed_refresh_token",
    )

    mock_blacklist.assert_awaited_once()

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_all_success(
    auth_service,
    mock_session,
    valid_stored_token,
) -> None:
    refresh_token = "valid_refresh_token"

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    access_token_version = 0

    with patch(
        "app.modules.auth.services.hash_refresh_token",
        return_value="hashed_refresh_token",
    ) as mock_hash:
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=valid_stored_token,
        )

        auth_service.refresh_token_repository.revoke_user = AsyncMock()

        auth_service.user_repository.increment_token_version = AsyncMock(
            side_effect=lambda user: setattr(
                user,
                "token_version",
                user.token_version + 1,
            ),
        )

        await auth_service.logout_all(
            refresh_token,
            current_user,
            access_token_version,
        )

    mock_hash.assert_called_once_with(refresh_token)

    auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "hashed_refresh_token",
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        current_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        current_user,
    )

    mock_session.commit.assert_awaited_once()

    assert current_user.token_version == 1


@pytest.mark.asyncio
async def test_logout_all_empty_refresh_token(
    auth_service,
    mock_session,
) -> None:
    refresh_token = None

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    access_token_version = 0

    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    auth_service.user_repository.increment_token_version = AsyncMock(
        side_effect=lambda user: setattr(
            user,
            "token_version",
            user.token_version + 1,
        ),
    )

    await auth_service.logout_all(
        refresh_token,
        current_user,
        access_token_version,
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        current_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        current_user,
    )

    mock_session.commit.assert_awaited_once()

    assert current_user.token_version == 1


@pytest.mark.asyncio
async def test_logout_all_refresh_token_not_found(
    auth_service,
    mock_session,
) -> None:
    refresh_token = "invalid_refresh_token"

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    access_token_version = 0

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            return_value="hashed_refresh_token",
        ) as mock_hash,
    ):
        auth_service.refresh_token_repository.get_by_hash = AsyncMock(
            return_value=None,
        )

        auth_service.refresh_token_repository.revoke_user = AsyncMock()

        auth_service.user_repository.increment_token_version = AsyncMock(
            side_effect=lambda user: setattr(
                user,
                "token_version",
                user.token_version + 1,
            ),
        )

        await auth_service.logout_all(
            refresh_token,
            current_user,
            access_token_version,
        )

    mock_hash.assert_called_once_with(refresh_token)

    auth_service.refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "hashed_refresh_token",
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        current_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        current_user,
    )

    mock_session.commit.assert_awaited_once()

    assert current_user.token_version == 1


@pytest.mark.asyncio
async def test_logout_all_idempotent(
    auth_service,
    mock_session,
) -> None:

    current_user = SimpleNamespace(
        id="user-123",
        token_version=0,
    )

    access_token_version = 0

    auth_service.refresh_token_repository.revoke_user = AsyncMock()

    auth_service.user_repository.increment_token_version = AsyncMock(
        side_effect=lambda user: setattr(
            user,
            "token_version",
            user.token_version + 1,
        ),
    )

    # First logout-all.
    await auth_service.logout_all(
        None,
        current_user,
        access_token_version,
    )

    assert current_user.token_version == 1

    # Repeat logout-all using the same access token.
    await auth_service.logout_all(
        None,
        current_user,
        access_token_version,
    )

    # Token version must not be incremented again.
    assert current_user.token_version == 1

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        current_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        current_user,
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_valid_refresh(
    auth_service,
    refresh_token_repository,
    user_repository,
    mock_session,
    refresh_token,
    valid_stored_token,
    active_user,
) -> None:
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.modules.auth.services.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.modules.auth.services.create_access_token",
            return_value="new-access-token",
        ),
    ):
        result = await auth_service.refresh(refresh_token)

    assert result.access_token == "new-access-token"
    assert result.refresh_token == "new-refresh-token"

    refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "old-token-hash",
        for_update=True,
    )

    user_repository.get_by_id.assert_awaited_once_with(
        active_user.id,
    )

    refresh_token_repository.revoke.assert_awaited_once_with(
        valid_stored_token.id,
    )

    refresh_token_repository.revoke_family.assert_not_awaited()

    refresh_token_repository.create.assert_awaited_once()

    create_kwargs = refresh_token_repository.create.await_args.kwargs

    assert create_kwargs["user_id"] == active_user.id
    assert create_kwargs["token_hash"] == "new-token-hash"
    assert create_kwargs["family_id"] == valid_stored_token.family_id
    assert create_kwargs["expires_at"] is not None

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_token_rotation(
    auth_service,
    refresh_token_repository,
    user_repository,
    mock_session,
    refresh_token,
    valid_stored_token,
    active_user,
) -> None:
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.modules.auth.services.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.modules.auth.services.create_access_token",
            return_value="new-access-token",
        ),
    ):
        await auth_service.refresh(refresh_token)

    refresh_token_repository.revoke.assert_awaited_once_with(
        valid_stored_token.id,
    )

    refresh_token_repository.create.assert_awaited_once()

    create_kwargs = refresh_token_repository.create.await_args.kwargs

    assert create_kwargs["token_hash"] == "new-token-hash"

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_family_preserved(
    auth_service,
    refresh_token_repository,
    user_repository,
    refresh_token,
    valid_stored_token,
    active_user,
) -> None:
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.modules.auth.services.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.modules.auth.services.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.modules.auth.services.create_access_token",
            return_value="new-access-token",
        ),
    ):
        await auth_service.refresh(refresh_token)

    create_kwargs = refresh_token_repository.create.await_args.kwargs

    assert create_kwargs["family_id"] == valid_stored_token.family_id

    refresh_token_repository.revoke_family.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_refresh_token(
    auth_service,
    refresh_token_repository,
    mock_session,
    refresh_token,
    expired_stored_token,
) -> None:

    refresh_token_repository.get_by_hash.return_value = expired_stored_token

    with patch(
        "app.modules.auth.services.hash_refresh_token",
        return_value="old-token-hash",
    ):
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh(refresh_token)

    refresh_token_repository.revoke.assert_not_awaited()
    refresh_token_repository.revoke_family.assert_not_awaited()
    refresh_token_repository.create.assert_not_awaited()

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_refresh_token(
    auth_service,
    refresh_token_repository,
    mock_session,
    refresh_token,
) -> None:

    refresh_token_repository.get_by_hash.return_value = None

    with patch(
        "app.modules.auth.services.hash_refresh_token",
        return_value="invalid-token-hash",
    ):
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh(refresh_token)

    refresh_token_repository.get_by_hash.assert_awaited_once_with(
        "invalid-token-hash",
        for_update=True,
    )

    refresh_token_repository.revoke.assert_not_awaited()
    refresh_token_repository.revoke_family.assert_not_awaited()
    refresh_token_repository.create.assert_not_awaited()

    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(
    auth_service,
    refresh_token_repository,
    mock_session,
    refresh_token,
    revoked_stored_token,
) -> None:

    refresh_token_repository.get_by_hash.return_value = revoked_stored_token

    with patch(
        "app.modules.auth.services.hash_refresh_token",
        return_value="old-token-hash",
    ):
        with pytest.raises(RefreshTokenReuseError):
            await auth_service.refresh(refresh_token)

    refresh_token_repository.revoke_family.assert_awaited_once_with(
        revoked_stored_token.family_id,
    )

    refresh_token_repository.revoke.assert_not_awaited()
    refresh_token_repository.create.assert_not_awaited()

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_registration(
    auth_service,
    mock_session,
    register_user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(return_value=None)
    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    with patch(
        "app.modules.auth.services.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        result = await auth_service.register(register_user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(register_user_payload.email),
    )

    mock_hash_password.assert_called_once_with(
        register_user_payload.password,
    )

    auth_service.user_repository.create.assert_awaited_once_with(
        email=str(register_user_payload.email),
        password_hash="hashed-password",
        full_name=register_user_payload.full_name,
    )

    mock_session.commit.assert_awaited_once()

    assert result is created_user


@pytest.mark.asyncio
async def test_duplicate_email(
    auth_service,
    mock_session,
    register_user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=created_user,
    )

    auth_service.user_repository.create = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(register_user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(register_user_payload.email),
    )

    auth_service.user_repository.create.assert_not_awaited()
    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_hashed(
    auth_service,
    mock_session,
    register_user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=None,
    )

    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    with patch(
        "app.modules.auth.services.hash_password",
        return_value="hashed-password",
    ) as mock_hash_password:
        await auth_service.register(register_user_payload)

    mock_hash_password.assert_called_once_with(
        register_user_payload.password,
    )

    auth_service.user_repository.create.assert_awaited_once_with(
        email=str(register_user_payload.email),
        password_hash="hashed-password",
        full_name=register_user_payload.full_name,
    )

    create_kwargs = auth_service.user_repository.create.await_args.kwargs

    assert create_kwargs["password_hash"] == "hashed-password"
    assert create_kwargs["password_hash"] != register_user_payload.password

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_integrity_error_handled(
    auth_service,
    mock_session,
    register_user_payload,
    created_user,
) -> None:
    auth_service.user_repository.get_by_email = AsyncMock(
        return_value=None,
    )

    auth_service.user_repository.create = AsyncMock(
        return_value=created_user,
    )

    integrity_error = IntegrityError(
        "INSERT INTO users",
        {},
        Exception("duplicate key"),
    )

    mock_session.commit.side_effect = integrity_error

    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(register_user_payload)

    auth_service.user_repository.get_by_email.assert_awaited_once_with(
        str(register_user_payload.email),
    )

    auth_service.user_repository.create.assert_awaited_once()

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_correct_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.modules.auth.services.verify_password",
        side_effect=[True, False],
    ) as mock_verify_password:
        with patch(
            "app.modules.auth.services.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
            )

    assert mock_verify_password.call_count == 2

    mock_verify_password.assert_any_call(
        current_password,
        created_user.password_hash,
    )

    mock_verify_password.assert_any_call(
        new_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_called_once_with(
        new_password,
    )

    auth_service.user_repository.update_password.assert_awaited_once_with(
        created_user,
        "new-hashed-password",
    )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        created_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        created_user,
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_incorrect_current_password(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "WrongPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.modules.auth.services.verify_password",
        return_value=False,
    ) as mock_verify_password:
        with patch(
            "app.modules.auth.services.hash_password",
        ) as mock_hash_password:
            with pytest.raises(InvalidCredentialsError):
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                )

    mock_verify_password.assert_called_once_with(
        current_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_not_called()

    auth_service.user_repository.update_password.assert_not_awaited()

    auth_service.refresh_token_repository.revoke_user.assert_not_awaited()

    auth_service.user_repository.increment_token_version.assert_not_awaited()

    mock_session.commit.assert_not_awaited()

    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_password_rejected(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "OldPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.modules.auth.services.verify_password",
        side_effect=[True, True],
    ) as mock_verify_password:
        with patch(
            "app.modules.auth.services.hash_password",
        ) as mock_hash_password:
            with pytest.raises(SamePasswordError):
                await auth_service.change_password(
                    created_user,
                    current_password,
                    new_password,
                )

    assert mock_verify_password.call_count == 2

    mock_verify_password.assert_any_call(
        current_password,
        created_user.password_hash,
    )

    mock_verify_password.assert_any_call(
        new_password,
        created_user.password_hash,
    )

    mock_hash_password.assert_not_called()

    auth_service.user_repository.update_password.assert_not_awaited()

    auth_service.refresh_token_repository.revoke_user.assert_not_awaited()

    auth_service.user_repository.increment_token_version.assert_not_awaited()

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_password_hashed(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.modules.auth.services.verify_password",
        side_effect=[True, False],
    ):
        with patch(
            "app.modules.auth.services.hash_password",
            return_value="new-hashed-password",
        ) as mock_hash_password:
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
            )

    mock_hash_password.assert_called_once_with(
        new_password,
    )

    auth_service.user_repository.update_password.assert_awaited_once_with(
        created_user,
        "new-hashed-password",
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_all_refresh_tokens(
    auth_service,
    mock_session,
    created_user,
) -> None:
    current_password = "OldPassword123"
    new_password = "NewPassword123"

    auth_service.user_repository.update_password = AsyncMock()
    auth_service.refresh_token_repository.revoke_user = AsyncMock()
    auth_service.user_repository.increment_token_version = AsyncMock()

    with patch(
        "app.modules.auth.services.verify_password",
        side_effect=[True, False],
    ):
        with patch(
            "app.modules.auth.services.hash_password",
            return_value="new-hashed-password",
        ):
            await auth_service.change_password(
                created_user,
                current_password,
                new_password,
            )

    auth_service.refresh_token_repository.revoke_user.assert_awaited_once_with(
        created_user.id,
    )

    auth_service.user_repository.increment_token_version.assert_awaited_once_with(
        created_user,
    )

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_success(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()
    token = "valid access token"

    created_user.id = uuid7()
    created_user.token_version = 0

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    mock_repository = AsyncMock()
    mock_repository.get_by_id.return_value = created_user

    with (
        patch(
            "app.api.v1.dependencies.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 0,
            },
        ),
        patch(
            "app.api.v1.dependencies.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_blacklist,
        patch(
            "app.api.v1.dependencies.UserRepository",
            return_value=mock_repository,
        ),
    ):
        result = await get_current_user(
            credentials=mock_credentials,
            session=mock_session,
            redis_client=mock_redis,
        )

    assert result is created_user

    mock_blacklist.assert_awaited_once_with(
        mock_redis,
        "jti-123",
    )

    mock_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )


@pytest.mark.asyncio
async def test_get_current_user_redis_miss(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()
    token = "valid access token"

    created_user.id = uuid7()
    created_user.token_version = 3

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    mock_repository = AsyncMock()
    mock_repository.get_by_id.return_value = created_user

    with (
        patch(
            "app.api.v1.dependencies.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 3,
            },
        ),
        patch(
            "app.api.v1.dependencies.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.api.v1.dependencies.UserRepository",
            return_value=mock_repository,
        ),
    ):
        result = await get_current_user(
            credentials=mock_credentials,
            session=mock_session,
            redis_client=mock_redis,
        )

    assert result is created_user

    mock_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )


@pytest.mark.asyncio
async def test_get_current_user_token_version_mismatch(
    mock_session,
    created_user,
) -> None:
    mock_redis = AsyncMock()

    created_user.id = uuid7()
    created_user.token_version = 2

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": "valid access token"},
    )()

    mock_repository = AsyncMock()

    with (
        patch(
            "app.api.v1.dependencies.decode_access_token",
            return_value={
                "sub": str(created_user.id),
                "jti": "jti-123",
                "token_version": 1,
            },
        ),
        patch(
            "app.api.v1.dependencies.is_access_token_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.api.v1.dependencies.UserRepository",
            return_value=mock_repository,
        ),
    ):
        from app.modules.auth.exceptions import InvalidTokenError

        with pytest.raises(InvalidTokenError):
            await get_current_user(
                credentials=mock_credentials,
                session=mock_session,
                redis_client=mock_redis,
            )

    mock_repository.get_by_id.assert_awaited_once_with(
        created_user.id,
    )
