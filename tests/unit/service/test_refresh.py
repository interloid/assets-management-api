from unittest.mock import patch

import pytest

from app.exceptions.auth import (
    InvalidTokenError,
    RefreshTokenReuseError,
)


@pytest.mark.asyncio
async def test_valid_refresh(
    auth_service,
    refresh_token_repository,
    user_repository,
    mock_session,
    refresh_token,
    valid_stored_token,
    active_user,
):
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.services.auth.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.services.auth.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.services.auth.create_access_token",
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
):
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.services.auth.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.services.auth.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.services.auth.create_access_token",
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
):
    refresh_token_repository.get_by_hash.return_value = valid_stored_token
    user_repository.get_by_id.return_value = active_user

    with (
        patch(
            "app.services.auth.hash_refresh_token",
            side_effect=[
                "old-token-hash",
                "new-token-hash",
            ],
        ),
        patch(
            "app.services.auth.generate_refresh_token",
            return_value="new-refresh-token",
        ),
        patch(
            "app.services.auth.create_access_token",
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
):

    refresh_token_repository.get_by_hash.return_value = expired_stored_token

    with patch(
        "app.services.auth.hash_refresh_token",
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
):

    refresh_token_repository.get_by_hash.return_value = None

    with patch(
        "app.services.auth.hash_refresh_token",
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
):

    refresh_token_repository.get_by_hash.return_value = revoked_stored_token

    with patch(
        "app.services.auth.hash_refresh_token",
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
