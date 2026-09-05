from app.models.refresh_token import RefreshToken


def test_refresh_token_columns() -> None:
    table = RefreshToken.__table__

    assert table.c.id.primary_key
    assert not table.c.user_id.nullable
    assert not table.c.token_hash.nullable
    assert not table.c.family_id.nullable
    assert not table.c.expires_at.nullable
    assert table.c.revoked_at.nullable
    assert not table.c.created_at.nullable


def test_refresh_token_hash() -> None:
    column = RefreshToken.__table__.c.token_hash

    assert column.type.python_type is str
    assert column.unique
    assert not column.nullable


def test_refresh_token_user_foreign_key() -> None:
    column = RefreshToken.__table__.c.user_id

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_refresh_token_user_id_index() -> None:
    table = RefreshToken.__table__

    assert any(index.name == "ix_refresh_tokens_user_id" for index in table.indexes)


def test_refresh_token_created_at() -> None:
    column = RefreshToken.__table__.c.created_at

    assert not column.nullable
    assert column.server_default is not None
