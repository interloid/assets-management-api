import pytest


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {
        "email": "test@example.com",
        "password": "Password123",
        "full_name": "Test User",
    }
