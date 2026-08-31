import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_accepts_valid_data() -> None:
    request = RegisterRequest(
        email="user@example.com",
        password="Password123",
        full_name="Test User",
    )

    assert request.email == "user@example.com"
    assert request.password == "Password123"
    assert request.full_name == "Test User"


def test_register_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="invalid-email",
            password="Password123",
            full_name="Test User",
        )


@pytest.mark.parametrize(
    "password",
    [
        "Pass1",
        "12345678",
        "Password",
    ],
)
def test_register_request_rejects_invalid_password(
    password: str,
) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="user@example.com",
            password=password,
            full_name="Test User",
        )


@pytest.mark.parametrize(
    "password",
    [
        "Password1",
        "Secure123",
        "TestPass99",
    ],
)
def test_register_request_accepts_valid_password(
    password: str,
) -> None:
    request = RegisterRequest(
        email="user@example.com",
        password=password,
        full_name="Test User",
    )

    assert request.password == password
