import csv
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from app.modules.asset.models import Asset  # noqa: F401
from app.shared.models.background_job import BackgroundJob  # noqa: F401
from app.shared.models.enums import AssetStatus, AssetType, WarrantyExpiry

CSV_COLUMNS = [
    "id",
    "asset_tag",
    "type",
    "serial_number",
    "status",
    "assigned_user_name",
    "assigned_user_email",
    "purchase_date",
    "warranty_expiry",
    "notes",
    "created_at",
    "updated_at",
]


def csv_value(value):
    if value is None:
        return ""

    if hasattr(value, "value"):
        return value.value

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    return value


def asset_to_csv(asset: Asset) -> dict:
    assigned_user = asset.assigned_user

    return {
        "id": asset.id,
        "asset_tag": asset.asset_tag,
        "type": asset.type,
        "serial_number": asset.serial_number,
        "status": asset.status,
        "assigned_user_name": (assigned_user.full_name if assigned_user else None),
        "assigned_user_email": (assigned_user.email if assigned_user else None),
        "purchase_date": asset.purchase_date,
        "warranty_expiry": asset.warranty_expiry,
        "notes": asset.notes,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def parse_filters(filters: dict) -> dict:
    parsed = dict(filters)

    if parsed.get("asset_type"):
        parsed["asset_type"] = AssetType(parsed["asset_type"])

    if parsed.get("asset_status"):
        parsed["asset_status"] = AssetStatus(parsed["asset_status"])

    if parsed.get("assigned_to"):
        parsed["assigned_to"] = UUID(str(parsed["assigned_to"]))

    if parsed.get("warranty_expiry"):
        parsed["warranty_expiry"] = WarrantyExpiry(parsed["warranty_expiry"])

    return parsed


def write_csv_file(file_path: Path, rows: list[dict]) -> int:
    with file_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow({key: csv_value(value) for key, value in row.items()})

    return len(rows)
