import re

SERIAL_REGEX = r"^[A-Z0-9-]+$"


def validate_serial_number(value: str) -> str:

    value = value.strip()

    if not value:
        raise ValueError("Serial number cannot be empty")

    if len(value) < 8:
        raise ValueError("Serial number must be at least 8 characters")

    if len(value) > 20:
        raise ValueError("Serial number must be within 20 characters")

    if not re.match(SERIAL_REGEX, value):
        raise ValueError(
            "Serial number must contain only uppercase letters, digits, and hyphens"
        )

    return value
