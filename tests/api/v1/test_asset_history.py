from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.user.models import User
from tests.api.v1.test_assets import create_asset, user_token


@pytest.mark.asyncio
async def test_admin_can_get_asset_history(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_admin: User,
    asset_owner: User,
):
    integration_client.cookies.set("access_token", admin_access_token)

    asset = await create_asset(
        integration_client, admin_access_token, serial_number="SN-HISTORY-001"
    )

    assign_response = await integration_client.post(
        f"api/v1/assets/{asset['id']}/assign",
        json={"user_id": str(asset_owner.id)},
    )

    assert assign_response.status_code == 200

    unassign_response = await integration_client.post(
        f"api/v1/assets/{asset['id']}/unassign",
    )

    assert unassign_response.status_code == 200

    response = await integration_client.get(f"api/v1/assets/{asset['id']}/assignments")

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["asset_id"] == asset["id"]
    assert len(body["data"]["history"]) == 1

    history = body["data"]["history"][0]
    assert history["assignee"]["id"] == str(asset_owner.id)
    assert history["assigned_by"]["id"] == str(integration_admin.id)
    assert history["returned_at"] is not None


@pytest.mark.asyncio
async def test_non_admin_cannot_get_asset_history(
    integration_client: AsyncClient,
    integration_user: User,
    admin_access_token: str,
):
    asset = await create_asset(
        integration_client,
        admin_access_token,
    )

    integration_client.cookies.set("access_token", user_token(integration_user))

    response = await integration_client.get(f"api/v1/assets/{asset['id']}/assignments")

    assert response.status_code == 403
    assert response.json()["error_code"] == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_asset_history_returns_404_for_missing_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    integration_client.cookies.set(
        "access_token",
        admin_access_token,
    )

    response = await integration_client.get(
        f"/api/v1/assets/{uuid4()}/assignments",
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_asset_history_returns_empty_list_when_no_assignments(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    integration_client.cookies.set(
        "access_token",
        admin_access_token,
    )

    asset = await create_asset(
        integration_client,
        admin_access_token,
    )

    response = await integration_client.get(f"api/v1/assets/{asset['id']}/assignments")

    assert response.status_code == 200
    assert response.json()["data"]["history"] == []


@pytest.mark.asyncio
async def test_user_can_get_own_assignement_history(
    integration_client: AsyncClient,
    integration_user: User,
    admin_access_token: str,
):
    asset = await create_asset(
        integration_client,
        admin_access_token,
    )

    integration_client.cookies.set(
        "access_token",
        admin_access_token,
    )

    assign_response = await integration_client.post(
        f"api/v1/assets/{asset['id']}/assign",
        json={
            "user_id": str(integration_user.id),
        },
    )

    assert assign_response.status_code == 200

    integration_client.cookies.set(
        "access_token",
        user_token(integration_user),
    )

    response = await integration_client.get(
        f"api/v1/users/{integration_user.id}/assignments",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["user_id"] == str(integration_user.id)
    assert len(body["data"]["assets"]) == 1
    assert body["data"]["assets"][0]["asset_id"] == asset["id"]


@pytest.mark.asyncio
async def test_user_cannot_get_another_users_assignment_history(
    integration_client: AsyncClient,
    integration_user: User,
    asset_owner: User,
):
    integration_client.cookies.set(
        "access_token",
        user_token(integration_user),
    )

    response = await integration_client.get(
        f"/api/v1/users/{asset_owner.id}/assignments",
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_admin_can_get_another_users_assignment_history(
    integration_client: AsyncClient,
    integration_admin: User,
    asset_owner: User,
    admin_access_token: str,
):
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        f"/api/v1/users/{asset_owner.id}/assignments",
    )

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == str(asset_owner.id)


@pytest.mark.asyncio
async def test_user_assignment_history_returns_404_for_missing_user(
    integration_client: AsyncClient,
    admin_access_token: str,
):
    integration_client.cookies.set("access_token", admin_access_token)

    response = await integration_client.get(
        f"/api/v1/users/{uuid4()}/assignments",
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "ASSET_ASSIGNMENT_USER_NOT_FOUND"
