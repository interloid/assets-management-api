from uuid import uuid4

import pytest

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_admin_list_users(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    integration_client.cookies.set("access_token", admin_access_token)
    response = await integration_client.get(
        "/api/v1/users",
    )

    assert response.status_code == 200

    body = response.json()

    assert "data" in body
    assert "pagination_meta" in body

    assert body["pagination_meta"]["page"] == 1
    assert body["pagination_meta"]["records_per_page"] == 20
    assert body["pagination_meta"]["total_items"] == 2
    assert body["pagination_meta"]["total_pages"] == 1

    assert len(body["data"]) == 2

    user = next(item for item in body["data"] if item["id"] == str(integration_user.id))

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
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        "/api/v1/users?page=1&size=1",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["pagination_meta"]["page"] == 1
    assert body["pagination_meta"]["records_per_page"] == 1
    assert body["pagination_meta"]["total_items"] == 2
    assert body["pagination_meta"]["total_pages"] == 2

    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_admin_list_users_search_by_email(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        f"/api/v1/users?search={integration_user.email}",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["pagination_meta"]["total_items"] == 1
    assert body["pagination_meta"]["total_pages"] == 1

    user = body["data"][0]

    assert user["id"] == str(integration_user.id)
    assert user["email"] == integration_user.email


@pytest.mark.asyncio
async def test_admin_list_users_search_by_full_name(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        "/api/v1/users?search=Refresh Token",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["pagination_meta"]["total_items"] == 1
    assert body["pagination_meta"]["total_pages"] == 1

    user = body["data"][0]

    assert user["id"] == str(integration_user.id)
    assert user["full_name"] == integration_user.full_name


@pytest.mark.asyncio
async def test_admin_list_users_search_is_case_insensitive(
    integration_client,
    admin_access_token,
    integration_user,
) -> None:
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        "/api/v1/users?search=REFRESH TOKEN",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["pagination_meta"]["total_items"] == 1
    assert body["pagination_meta"]["total_pages"] == 1

    assert body["data"][0]["id"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(
    integration_client,
    integration_user,
) -> None:
    access_token = create_access_token(
        user_id=str(integration_user.id),
        role=integration_user.role.value,
        token_version=integration_user.token_version,
        family_id=str(uuid4()),
    )
    integration_client.cookies.set("access_token", access_token)

    response = await integration_client.get(
        "/api/v1/users",
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_rejects_size_above_100(
    integration_client,
    admin_access_token,
) -> None:
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        "/api/v1/users?size=101",
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list_users(
    integration_client,
) -> None:
    response = await integration_client.get(
        "/api/v1/users",
    )

    assert response.status_code == 401

    body = response.json()

    assert body["error_code"] == "AUTHENTICATION_REQUIRED"
