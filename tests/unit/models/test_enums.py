from app.models.enums import AssetStatus, AssetType, UserRole


def test_user_role() -> None:
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.USER.value == "user"


def test_asset_status() -> None:
    assert AssetStatus.IN_STOCK.value == "in_stock"
    assert AssetStatus.ASSIGNED.value == "assigned"
    assert AssetStatus.REPAIR.value == "repair"
    assert AssetStatus.RETIRED.value == "retired"


def test_asset_type() -> None:
    assert AssetType.MONITOR.value == "monitor"
    assert AssetType.LAPTOP.value == "laptop"
    assert AssetType.PHONE.value == "phone"
    assert AssetType.ACCESSORY.value == "accessory"
