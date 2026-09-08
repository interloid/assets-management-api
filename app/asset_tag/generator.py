from app.core.config import settings
from app.models.enums import AssetType

ASSET_TYPE_PREFIXES: dict[AssetType, str] = {
    AssetType.LAPTOP: "LAP",
    AssetType.MONITOR: "MON",
    AssetType.PHONE: "PHN",
    AssetType.ACCESSORY: "ACC",
}


def get_company_prefix() -> str:
    return settings.ASSET_TAG_COMPANY_PREFIX.strip().upper()


def build_asset_tag(
    asset_type: AssetType,
    number: int,
) -> str:
    try:
        type_prefix = ASSET_TYPE_PREFIXES[asset_type]

    except KeyError as exc:
        raise ValueError(f"Unsupported asset type: {asset_type}") from exc

    company_prefix = get_company_prefix()
    return f"{company_prefix}-{type_prefix}-{number:04d}"
