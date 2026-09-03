from unittest.mock import AsyncMock, patch

import pytest

from app.dependencies.authentication import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_success(
    mock_session,
    created_user,
) -> None:
    token = "valid access token"

    mock_credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    mock_repository = AsyncMock()
    mock_repository.get_by_id.return_value = created_user

    with (
        patch(
            "app.dependencies.authentication.decode_access_token",
            return_value={"sub": str(created_user.id)},
        ),
        patch(
            "app.dependencies.authentication.UserRepository",
            return_value=mock_repository,
        ),
    ):
        result = await get_current_user(
            credentials=mock_credentials,
            session=mock_session,
        )

        assert result == created_user

        mock_repository.get_by_id.assert_awaited_once_with(
            str(created_user.id),
        )
