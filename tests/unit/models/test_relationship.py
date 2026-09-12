from app.models.assets import Asset
from app.models.refresh_token import RefreshToken
from app.models.user import User


def test_user_refresh_tokens_relationship() -> None:
    relationship = User.__mapper__.relationships["refresh_tokens"]

    assert relationship.mapper.class_ is RefreshToken
    assert relationship.back_populates == "user"


def test_refresh_token_user_relationship() -> None:
    relationship = RefreshToken.__mapper__.relationships["user"]

    assert relationship.mapper.class_ is User
    assert relationship.back_populates == "refresh_tokens"


def test_user_assets_relationship() -> None:
    relationship = User.__mapper__.relationships["assets"]

    assert relationship.mapper.class_ is Asset
    assert relationship.back_populates == "assigned_user"


def test_asset_assigned_user_relationship() -> None:
    relationship = Asset.__mapper__.relationships["assigned_user"]

    assert relationship.mapper.class_ is User
    assert relationship.back_populates == "assets"
