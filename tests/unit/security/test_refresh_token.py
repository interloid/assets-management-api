from app.core.security import generate_refresh_token, hash_refresh_token


def test_sec_08_refresh_token_is_random() -> None:
    tokens = {generate_refresh_token() for _ in range(10)}

    assert len(tokens) == 10


def test_sec_09_refresh_token_is_hashed() -> None:
    raw_token = generate_refresh_token()

    token_hash = hash_refresh_token(raw_token)

    assert token_hash != raw_token
    assert len(token_hash) == 64
