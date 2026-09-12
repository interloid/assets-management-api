import pytest

from app.schemas.auth import validate_password


def test_valid_password() -> None:
    password = "Password123"

    assert validate_password(password) == password


def test_password_must_have_minimum_length() -> None:
    with pytest.raises(
        ValueError,
        match="Password must be at least 8 characters long",
    ):
        validate_password("Pass123")


def test_password_must_contain_letter() -> None:
    with pytest.raises(
        ValueError,
        match="Password must contain at least one letter",
    ):
        validate_password("12345678")


def test_password_must_contain_digit() -> None:
    with pytest.raises(
        ValueError,
        match="Password must contain at least one digit",
    ):
        validate_password("Password")


def test_password_with_letter_and_digit_is_valid() -> None:
    password = "abcdefgh1"

    assert validate_password(password) == password
