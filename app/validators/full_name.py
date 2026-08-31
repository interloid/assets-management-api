import re


def validate_full_name(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Full name cannot be empty")

    if len(value) < 2:
        raise ValueError("Full name must be at least 2 characters long")

    if len(value) > 100:
        raise ValueError("Full name must not exceed 100 characters")

    if not re.match(r"^[A-Za-z]", value):
        raise ValueError("Full name must start with a letter")

    if "  " in value:
        raise ValueError("Full name must not contain consecutive spaces")

    if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", value):
        raise ValueError(
            "Full name can contain only letters, spaces, hyphens, and apostrophes"
        )

    return value
