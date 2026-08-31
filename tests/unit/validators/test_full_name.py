import pytest

from app.validators.full_name import validate_full_name


@pytest.mark.parametrize(
    "full_name",
    [
        "John Doe",
        "Mary-Jane Watson",
        "O'Connor",
    ],
)
def test_validate_full_name_accepts_valid_names(
    full_name: str,
) -> None:
    assert validate_full_name(full_name) == full_name


@pytest.mark.parametrize(
    "full_name,expected_message",
    [
        ("   ", "Full name cannot be empty"),
        ("J", "Full name must be at least 2 characters long"),
        ("A" * 101, "Full name must not exceed 100 characters"),
        ("123 John", "Full name must start with a letter"),
        (
            "John@Doe",
            "Full name can contain only letters, spaces, hyphens, and apostrophes",
        ),
        ("John  Doe", "Full name must not contain consecutive spaces"),
    ],
)
def test_validate_full_name_rejects_invalid_names(
    full_name: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        validate_full_name(full_name)


def test_validate_full_name_strips_whitespace() -> None:
    assert validate_full_name("  John Doe  ") == "John Doe"
