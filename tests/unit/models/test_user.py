from sqlalchemy.dialects.postgresql import CITEXT

from app.models.user import User


def test_user_coloumns():
    table = User.__table__

    assert table.c.id.primary_key
    assert not table.c.email.nullable
    assert not table.c.password_hash.nullable
    assert not table.c.full_name.nullable
    assert not table.c.role.nullable
    assert not table.c.is_active.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable


def test_user_defaults():
    table = User.__table__

    assert str(table.c.role.server_default.arg) == "user"
    assert str(table.c.is_active.server_default.arg) == "true"
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None


def test_user_email():
    column = User.__table__.c.email

    assert isinstance(column.type, CITEXT)
    assert column.unique
    assert not column.nullable


def test_user_updated_at_onupdate():
    column = User.__table__.c.updated_at

    assert column.onupdate is not None
