def validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not any(char.isalpha() for char in value):
        raise ValueError("Password must contain at least one letter")

    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one digit")

    return value
