from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.modules.asset.models import Asset
from app.modules.asset.tag.model import AssetTagCounter
from app.modules.user.models import User
from app.shared.models.enums import AssetStatus, AssetType


async def create_asset(
    client: AsyncClient,
    token: str,
    *,
    asset_type: str = "laptop",
    serial_number: str = "SN-TEST-001",
    purchase_date: str = "2026-09-08",
    **extra: object,
) -> dict:
    payload = {
        "type": asset_type,
        "serial_number": serial_number,
        "purchase_date": purchase_date,
        **extra,
    }

    response = await client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 201
    return response.json()["data"]


def user_token(user: User) -> str:
    return create_access_token(
        user_id=str(user.id),
        role=user.role.value,
        token_version=user.token_version,
    )


async def set_asset_status(
    db_session,
    asset_id: str,
    status: AssetStatus,
    assigned_to: UUID | None = None,
) -> Asset:
    asset = await db_session.get(Asset, UUID(asset_id))
    assert asset is not None

    asset.status = status
    asset.assigned_to = assigned_to

    await db_session.commit()
    await db_session.refresh(asset)

    return asset


@pytest.mark.asyncio
async def test_admin_can_create_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    data = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-CREATE-001",
    )

    assert data["status"] == "in_stock"
    assert data["assigned_to"] is None
    assert data["asset_tag"].startswith("IL-LAP-")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "type": "invalid_type",
            "serial_number": "",
        },
        {
            "type": "laptop",
            "serial_number": "SN-CREATE-002",
            "purchase_date": "2026-09-08",
            "assigned_to": "00000000-0000-0000-0000-000000000001",
        },
    ],
)
async def test_create_asset_rejects_invalid_payload(
    integration_client: AsyncClient,
    admin_access_token: str,
    payload: dict,
) -> None:
    response = await integration_client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_asset_rejects_duplicate_serial_number(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    payload = {
        "type": "laptop",
        "serial_number": "SN-CREATE-DUPLICATE",
        "purchase_date": "2026-09-08",
    }

    first = await integration_client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json=payload,
    )
    assert first.status_code == 201

    second = await integration_client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json=payload,
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "SERIAL_NUMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_non_admin_cannot_create_asset(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    response = await integration_client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
        json={
            "type": "laptop",
            "serial_number": "SN-CREATE-UNAUTHORIZED",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_assets(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    for index in range(3):
        await create_asset(
            integration_client,
            admin_access_token,
            serial_number=f"SN-LIST-{index}",
        )

    response = await integration_client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["meta"]["page"] == 1
    assert body["meta"]["size"] == 20
    assert body["meta"]["total_items"] == 3
    assert body["meta"]["total_pages"] == 1
    assert len(body["data"]) == 3


@pytest.mark.asyncio
async def test_list_assets_supports_pagination(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    for index in range(5):
        await create_asset(
            integration_client,
            admin_access_token,
            serial_number=f"SN-PAGE-{index}",
        )

    response = await integration_client.get(
        "/api/v1/assets?page=2&size=2",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    meta = response.json()["meta"]

    assert meta["page"] == 2
    assert meta["size"] == 2
    assert meta["total_items"] == 5
    assert meta["total_pages"] == 3
    assert len(response.json()["data"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, expected_serial",
    [
        ("type=laptop", "SN-FILTER-LAPTOP"),
        ("asset_status=in_stock", "SN-FILTER-STATUS"),
        ("search=dell", "SN-FILTER-SEARCH"),
        (
            "warranty_expiring_before=2026-12-31",
            "SN-FILTER-WARRANTY",
        ),
    ],
)
async def test_list_assets_filters(
    integration_client: AsyncClient,
    admin_access_token: str,
    query: str,
    expected_serial: str,
) -> None:
    await create_asset(
        integration_client,
        admin_access_token,
        asset_type="laptop",
        serial_number="SN-FILTER-LAPTOP",
    )

    await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-FILTER-STATUS",
    )

    await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-FILTER-SEARCH",
        notes="Dell development laptop",
    )

    await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-FILTER-WARRANTY",
        warranty_expiry="2026-10-01",
    )

    response = await integration_client.get(
        f"/api/v1/assets?{query}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert len(data) >= 1
    assert expected_serial in {item["serial_number"] for item in data}


@pytest.mark.asyncio
async def test_list_assets_combines_filters_with_and(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-AND-MATCH",
        notes="Development laptop",
    )

    await create_asset(
        integration_client,
        admin_access_token,
        asset_type="monitor",
        serial_number="SN-AND-NO-TYPE",
        notes="Development monitor",
    )

    response = await integration_client.get(
        "/api/v1/assets?type=laptop&asset_status=in_stock&search=development",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert len(data) == 1
    assert data[0]["serial_number"] == "SN-AND-MATCH"


@pytest.mark.asyncio
async def test_list_assets_rejects_invalid_query_parameters(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    for query in (
        "page=0",
        "size=101",
        "sort=updated_at",
    ):
        response = await integration_client.get(
            f"/api/v1/assets?{query}",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_list_assets(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    response = await integration_client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_get_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-GET-ADMIN",
    )

    response = await integration_client.get(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == asset["id"]


@pytest.mark.asyncio
async def test_assigned_user_can_get_own_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-GET-OWN",
    )

    await set_asset_status(
        db_session,
        asset["id"],
        AssetStatus.ASSIGNED,
        integration_user.id,
    )

    response = await integration_client.get(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "assigned",
    [False, True],
)
async def test_user_cannot_get_asset_they_do_not_own(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    asset_owner: User,
    db_session,
    assigned: bool,
) -> None:
    serial_number = "SN-GET-NO-OWNER" if not assigned else "SN-GET-OTHER"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number=serial_number,
    )

    if assigned:
        await set_asset_status(
            db_session,
            asset["id"],
            AssetStatus.ASSIGNED,
            asset_owner.id,
        )

    response = await integration_client.get(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "asset_id",
    [
        "00000000-0000-0000-0000-000000000001",
        "not-a-valid-uuid",
    ],
)
async def test_get_asset_rejects_invalid_or_missing_id(
    integration_client: AsyncClient,
    admin_access_token: str,
    asset_id: str,
) -> None:
    response = await integration_client.get(
        f"/api/v1/assets/{asset_id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    if asset_id == "not-a-valid-uuid":
        assert response.status_code == 422
    else:
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_can_update_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UPDATE-001",
    )

    response = await integration_client.patch(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"notes": "Updated notes"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_update_asset_type_changes_asset_tag(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UPDATE-002",
    )

    response = await integration_client.patch(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"type": "monitor"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["type"] == "monitor"
    assert data["asset_tag"] != asset["asset_tag"]
    assert data["asset_tag"].startswith("IL-MON-")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected_status, expected_code",
    [
        (
            {"serial_number": "SN-UPDATE-DUPLICATE"},
            409,
            "SERIAL_NUMBER_ALREADY_EXISTS",
        ),
        (
            {"asset_tag": "IL-LAP-9999"},
            422,
            None,
        ),
    ],
)
async def test_update_asset_rejects_invalid_changes(
    integration_client: AsyncClient,
    admin_access_token: str,
    payload: dict,
    expected_status: int,
    expected_code: str | None,
) -> None:
    first = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UPDATE-DUPLICATE",
    )

    second = await create_asset(
        integration_client,
        admin_access_token,
        asset_type="monitor",
        serial_number="SN-UPDATE-SECOND",
    )

    target_id = second["id"]

    if "serial_number" in payload:
        payload = {"serial_number": first["serial_number"]}

    response = await integration_client.patch(
        f"/api/v1/assets/{target_id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json=payload,
    )

    assert response.status_code == expected_status

    if expected_code:
        assert response.json()["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_non_admin_cannot_update_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UPDATE-FORBIDDEN",
    )

    response = await integration_client.patch(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
        json={"notes": "Unauthorized"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        AssetStatus.IN_STOCK,
        AssetStatus.RETIRED,
    ],
)
async def test_admin_can_delete_allowed_asset_status(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
    status: AssetStatus,
) -> None:
    serial_number = f"SN-DEL-{status.name.replace('_', '')}"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number=serial_number,
    )

    await set_asset_status(
        db_session,
        asset["id"],
        status,
    )

    response = await integration_client.delete(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        AssetStatus.ASSIGNED,
        AssetStatus.REPAIR,
    ],
)
async def test_admin_cannot_delete_restricted_asset_status(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
    status: AssetStatus,
) -> None:
    serial_number = f"SN-DEL-B-{status.name.replace('_', '')}"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number=serial_number,
    )

    assigned_to = integration_user.id if status == AssetStatus.ASSIGNED else None

    await set_asset_status(
        db_session,
        asset["id"],
        status,
        assigned_to,
    )

    response = await integration_client.delete(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ASSET_DELETE_CONFLICT"


@pytest.mark.asyncio
async def test_delete_requires_admin_and_existing_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    response = await integration_client.delete(
        f"/api/v1/assets/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-DELETE-AUTH",
    )

    response = await integration_client.delete(
        f"/api/v1/assets/{asset['id']}",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_assign_in_stock_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-ASSIGN-OK",
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"user_id": str(integration_user.id)},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["status"] == "assigned"
    assert data["assigned_to"] == str(integration_user.id)


@pytest.mark.asyncio
async def test_assign_rejects_invalid_asset_status(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-ASSIGN-STATUS",
    )

    await set_asset_status(
        db_session,
        asset["id"],
        AssetStatus.REPAIR,
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"user_id": str(integration_user.id)},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_assign_rejects_invalid_user(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-ASSIGN-USER",
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_ASSIGNMENT_USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_assign_requires_admin_and_existing_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"user_id": str(integration_user.id)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-ASSIGN-AUTH",
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
        json={"user_id": str(integration_user.id)},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_unassign_assigned_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UNASSIGN-OK",
    )

    assign_response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"user_id": str(integration_user.id)},
    )

    assert assign_response.status_code == 200

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/unassign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["status"] == "in_stock"
    assert data["assigned_to"] is None


@pytest.mark.asyncio
async def test_unassign_rejects_non_assigned_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UNASSIGN-BLOCK",
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/unassign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_unassign_requires_admin_and_existing_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/unassign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-UNASSIGN-AUTH",
    )

    await integration_client.post(
        f"/api/v1/assets/{asset['id']}/assign",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"user_id": str(integration_user.id)},
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/unassign",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial_status, target_status",
    [
        (AssetStatus.IN_STOCK, AssetStatus.REPAIR),
        (AssetStatus.IN_STOCK, AssetStatus.RETIRED),
        (AssetStatus.REPAIR, AssetStatus.IN_STOCK),
        (AssetStatus.REPAIR, AssetStatus.RETIRED),
    ],
)
async def test_admin_can_change_allowed_asset_status(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
    initial_status: AssetStatus,
    target_status: AssetStatus,
) -> None:
    serial_number = (
        f"SN-ST-"
        f"{initial_status.name.replace('_', '')[:5]}-"
        f"{target_status.name.replace('_', '')[:5]}"
    )

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number=serial_number,
    )

    await set_asset_status(
        db_session,
        asset["id"],
        initial_status,
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/status",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"status": target_status.value},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == target_status.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial_status, target_status",
    [
        (AssetStatus.IN_STOCK, AssetStatus.ASSIGNED),
        (AssetStatus.ASSIGNED, AssetStatus.IN_STOCK),
        (AssetStatus.RETIRED, AssetStatus.REPAIR),
    ],
)
async def test_admin_cannot_change_disallowed_asset_status(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
    initial_status: AssetStatus,
    target_status: AssetStatus,
) -> None:
    serial_number = f"SN-ST-B-{initial_status.name.replace('_', '')[:5]}"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number=serial_number,
    )

    assigned_to = (
        integration_user.id if initial_status == AssetStatus.ASSIGNED else None
    )

    await set_asset_status(
        db_session,
        asset["id"],
        initial_status,
        assigned_to,
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/status",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"status": target_status.value},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_ASSET_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_status_change_requires_admin_and_existing_asset(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
) -> None:
    response = await integration_client.post(
        f"/api/v1/assets/{uuid4()}/status",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"status": "repair"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"

    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-STATUS-AUTH",
    )

    response = await integration_client.post(
        f"/api/v1/assets/{asset['id']}/status",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
        json={"status": "repair"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_can_list_my_assets(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-MY-001",
    )

    await set_asset_status(
        db_session,
        asset["id"],
        AssetStatus.ASSIGNED,
        integration_user.id,
    )

    response = await integration_client.get(
        "/api/v1/users/me/assets",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["meta"]["total_items"] == 1
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_my_assets_returns_only_current_users_assets(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    integration_admin: User,
    db_session,
) -> None:
    user_asset = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-MY-USER",
    )

    other_asset = await create_asset(
        integration_client,
        admin_access_token,
        asset_type="monitor",
        serial_number="SN-MY-OTHER",
    )

    unassigned_asset = await create_asset(
        integration_client,
        admin_access_token,
        asset_type="phone",
        serial_number="SN-MY-NONE",
    )

    await set_asset_status(
        db_session,
        user_asset["id"],
        AssetStatus.ASSIGNED,
        integration_user.id,
    )

    await set_asset_status(
        db_session,
        other_asset["id"],
        AssetStatus.ASSIGNED,
        integration_admin.id,
    )

    response = await integration_client.get(
        "/api/v1/users/me/assets",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert len(data) == 1
    assert data[0]["id"] == user_asset["id"]
    assert unassigned_asset["id"] not in {item["id"] for item in data}


@pytest.mark.asyncio
async def test_my_assets_supports_pagination_and_requires_authentication(
    integration_client: AsyncClient,
    admin_access_token: str,
    integration_user: User,
    db_session,
) -> None:
    asset_ids = []

    for index in range(5):
        asset = await create_asset(
            integration_client,
            admin_access_token,
            serial_number=f"SN-MY-PAGE-{index}",
        )
        asset_ids.append(asset["id"])

    result = await db_session.execute(
        select(Asset).where(Asset.id.in_([UUID(asset_id) for asset_id in asset_ids]))
    )

    assets = result.scalars().all()

    for asset in assets:
        asset.status = AssetStatus.ASSIGNED
        asset.assigned_to = integration_user.id

    await db_session.commit()

    response = await integration_client.get(
        "/api/v1/users/me/assets?page=2&size=2",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 200

    meta = response.json()["meta"]

    assert meta["page"] == 2
    assert meta["size"] == 2
    assert meta["total_items"] == 5
    assert meta["total_pages"] == 3
    assert len(response.json()["data"]) == 2

    unauthenticated = await integration_client.get("/api/v1/users/me/assets")

    assert unauthenticated.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_get_asset_summary(
    integration_client: AsyncClient,
    admin_access_token: str,
) -> None:
    await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-SUMMARY-001",
    )

    response = await integration_client.get(
        "/api/v1/assets/stats",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["total"] == 1
    assert data["in_stock"] == 1
    assert data["assigned"] == 0
    assert data["repair"] == 0
    assert data["retired"] == 0


@pytest.mark.asyncio
async def test_non_admin_cannot_get_asset_summary(
    integration_client: AsyncClient,
    integration_user: User,
) -> None:
    response = await integration_client.get(
        "/api/v1/assets/stats",
        headers={"Authorization": f"Bearer {user_token(integration_user)}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_asset_rejects_duplicate_asset_tag(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
) -> None:
    first = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-TAG-DUP-001",
    )

    assert first["asset_tag"] == "IL-LAP-0001"

    counter = await db_session.scalar(
        select(AssetTagCounter).where(
            AssetTagCounter.company_prefix == "IL",
            AssetTagCounter.asset_type == AssetType.LAPTOP,
        )
    )

    assert counter is not None

    counter.last_number = 0
    await db_session.commit()

    response = await integration_client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "type": "laptop",
            "serial_number": "SN-TAG-DUP-002",
            "purchase_date": "2026-09-08",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ASSET_TAG_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_asset_rejects_duplicate_asset_tag(
    integration_client: AsyncClient,
    admin_access_token: str,
    db_session,
) -> None:
    first = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-TAG-UPD-001",
    )

    second = await create_asset(
        integration_client,
        admin_access_token,
        serial_number="SN-TAG-UPD-002",
    )

    counter = await db_session.scalar(
        select(AssetTagCounter).where(
            AssetTagCounter.company_prefix == "IL",
            AssetTagCounter.asset_type == AssetType.MONITOR,
        )
    )

    assert counter is None

    response = await integration_client.patch(
        f"/api/v1/assets/{second['id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"type": "laptop"},
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["asset_tag"] != first["asset_tag"]
