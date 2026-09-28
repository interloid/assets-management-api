import app.shared.models  # noqa: F401
from app.modules.asset.models import Asset
from app.modules.auth.models import RefreshToken
from app.modules.user.models import User
from app.shared.models.base import Base


def test_all_models_registered() -> None:
    expected_tables = {"users", "refresh_tokens", "assets", "asset_tag_counters"}

    assert set(Base.metadata.tables.keys()) == expected_tables


def test_common_created_at() -> None:
    for model in (User, RefreshToken, Asset):
        column = model.__table__.c.created_at

        assert not column.nullable
        assert column.server_default is not None


def test_common_updated_at() -> None:
    for model in (User, Asset):
        column = model.__table__.c.updated_at

        assert not column.nullable
        assert column.server_default is not None
        assert column.onupdate is not None
