import app.models  # noqa: F401
from app.db.base import Base
from app.models.assets import Asset
from app.models.refresh_token import RefreshToken
from app.models.user import User


def test_all_models_registered():
    expected_tables = {"users", "refresh_tokens", "assets"}

    assert set(Base.metadata.tables.keys()) == expected_tables


def test_common_created_at():
    for model in (User, RefreshToken, Asset):
        column = model.__table__.c.created_at

        assert not column.nullable
        assert column.server_default is not None


def test_common_updated_at():
    for model in (User, Asset):
        column = model.__table__.c.updated_at

        assert not column.nullable
        assert column.server_default is not None
        assert column.onupdate is not None
