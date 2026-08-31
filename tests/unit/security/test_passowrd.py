from app.core.security import hash_password, verify_password


def test__password_is_argon_hashed() -> None:
    password = "Password123"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id")


def test_correct_password_verifies() -> None:
    password = "Password123"

    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_incorrect_password_fails() -> None:
    password = "Password123"
    wrong_password = "WrongPassword123"

    password_hash = hash_password(password)

    assert verify_password(wrong_password, password_hash) is False
