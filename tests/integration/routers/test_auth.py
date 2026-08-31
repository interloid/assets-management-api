import pytest


@pytest.mark.asyncio
async def test_register_returns_201(
    integration_client,
    user_payload,
) -> None:
    response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["email"] == user_payload["email"]
    assert body["full_name"] == user_payload["full_name"]


@pytest.mark.asyncio
async def test_register_does_not_return_password(
    integration_client,
    user_payload,
) -> None:
    response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert "password" not in body
    assert "password_hash" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "duplicate_email",
    [
        pytest.param(
            "test@example.com",
            id="exact-duplicate",
        ),
        pytest.param(
            "TEST@EXAMPLE.COM",
            id="uppercase-duplicate",
        ),
        pytest.param(
            "Test@Example.Com",
            id="mixed-case-duplicate",
        ),
    ],
)
async def test_register_returns_409_for_duplicate_email(
    integration_client,
    user_payload,
    duplicate_email,
) -> None:
    first_response = await integration_client.post(
        "/auth/register",
        json=user_payload,
    )

    assert first_response.status_code == 201

    duplicate_payload = {
        **user_payload,
        "email": duplicate_email,
    }

    second_response = await integration_client.post(
        "/auth/register",
        json=duplicate_payload,
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Email already registered",
    }


@pytest.mark.asyncio
async def test_register_returns_422_for_invalid_email(
    integration_client,
    user_payload,
) -> None:
    payload = {
        **user_payload,
        "email": "not-an-email",
    }

    response = await integration_client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    [
        "Pass1",
        "12345678",
        "Password",
    ],
)
async def test_register_returns_422_for_invalid_password(
    integration_client,
    user_payload,
    password,
) -> None:
    payload = {
        **user_payload,
        "password": password,
    }

    response = await integration_client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 422
