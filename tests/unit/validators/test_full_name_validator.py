import pytest

from app.schemas.auth import validate_full_name


def test_valid_full_name() -> None:
    assert validate_full_name("John Doe") == "John Doe"


def test_full_name_is_stripped() -> None:
    assert validate_full_name("  John Doe  ") == "John Doe"


@pytest.mark.parametrize(
    "full_name",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_full_name_cannot_be_empty(full_name: str) -> None:
    with pytest.raises(ValueError, match="Full name cannot be empty"):
        validate_full_name(full_name)


def test_full_name_minimum_length() -> None:
    assert validate_full_name("Ab") == "Ab"


def test_full_name_less_than_two_characters() -> None:
    with pytest.raises(
        ValueError,
        match="Full name must be at least 2 characters long",
    ):
        validate_full_name("A")


def test_full_name_maximum_length() -> None:
    full_name = "A" * 100

    assert validate_full_name(full_name) == full_name


def test_full_name_exceeds_maximum_length() -> None:
    with pytest.raises(
        ValueError,
        match="Full name must not exceed 100 characters",
    ):
        validate_full_name("A" * 101)


@pytest.mark.parametrize(
    "full_name",
    [
        "1John",
        "-John",
        "'John",
    ],
)
def test_full_name_must_start_with_letter(full_name: str) -> None:
    with pytest.raises(
        ValueError,
        match="Full name must start with a letter",
    ):
        validate_full_name(full_name)


@pytest.mark.parametrize(
    "full_name",
    [
        "John  Doe",
        "John   Doe",
        "John    Doe",
    ],
)
def test_full_name_cannot_contain_consecutive_spaces(
    full_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Full name must not contain consecutive spaces",
    ):
        validate_full_name(full_name)


@pytest.mark.parametrize(
    "full_name",
    [
        "John123",
        "John@Doe",
        "John_Doe",
        "John.Doe",
        "John/Doe",
        "John+Doe",
    ],
)
def test_full_name_allows_only_valid_characters(
    full_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Full name can contain only letters, spaces, hyphens, and apostrophes",
    ):
        validate_full_name(full_name)


@pytest.mark.parametrize(
    "full_name",
    [
        "John Doe",
        "John-Doe",
        "John'Doe",
        "Mary Jane Watson",
        "Mary-Jane Watson",
        "O'Connor",
    ],
)
def test_valid_full_name_formats(full_name: str) -> None:
    assert validate_full_name(full_name) == full_name
