import pytest

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_admin_list_users(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    response = await integration_client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["statusCode"] == 200
    assert body["message"] == "Users retrieved successfully"
    assert body["error"] is None

    assert body["data"]["page"] == 1
    assert body["data"]["size"] == 20
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 2

    user = next(
        item for item in body["data"]["items"] if item["id"] == str(integration_user.id)
    )

    assert user["email"] == integration_user.email
    assert user["full_name"] == integration_user.full_name
    assert user["role"] == integration_user.role.value

    assert "password_hash" not in user
    assert "is_active" not in user
    assert "created_at" not in user
    assert "updated_at" not in user


@pytest.mark.asyncio
async def test_admin_list_users_pagination(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    response = await integration_client.get(
        "/users?page=1&size=1",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["page"] == 1
    assert body["data"]["size"] == 1
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_admin_list_users_search_by_email(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    response = await integration_client.get(
        f"/users?search={integration_user.email}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1

    user = body["data"]["items"][0]

    assert user["id"] == str(integration_user.id)
    assert user["email"] == integration_user.email


@pytest.mark.asyncio
async def test_admin_list_users_search_by_full_name(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    response = await integration_client.get(
        "/users?search=Refresh Token",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1

    user = body["data"]["items"][0]

    assert user["id"] == str(integration_user.id)
    assert user["full_name"] == integration_user.full_name


@pytest.mark.asyncio
async def test_admin_list_users_search_is_case_insensitive(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    response = await integration_client.get(
        "/users?search=REFRESH TOKEN",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1

    assert body["data"]["items"][0]["id"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(
    integration_client,
    integration_user,
) -> None:
    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
    )

    response = await integration_client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403

    body = response.json()

    assert body["success"] is False
    assert body["statusCode"] == 403


@pytest.mark.asyncio
async def test_admin_list_users_rejects_size_above_100(
    integration_client,
    admin_access_token,
) -> None:
    response = await integration_client.get(
        "/users?size=101",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
        },
    )

    assert response.status_code == 422
