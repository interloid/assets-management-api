from app.core.security import hash_password, verify_password


def test_hash_password_does_not_return_plaintext() -> None:
    password = "Password123"

    password_hash = hash_password(password)

    assert password_hash != password


def test_hash_password_generates_different_hashes_for_same_password() -> None:
    password = "Password123"

    hash_1 = hash_password(password)
    hash_2 = hash_password(password)

    assert hash_1 != hash_2


def test_verify_password_returns_true_for_correct_password() -> None:
    password = "Password123"

    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_returns_false_for_incorrect_password() -> None:
    password = "Password123"

    password_hash = hash_password(password)

    assert (
        verify_password(
            "WrongPassword123",
            password_hash,
        )
        is False
    )
