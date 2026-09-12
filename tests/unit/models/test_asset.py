from app.models.assets import Asset


def test_asset_columns() -> None:
    table = Asset.__table__

    assert table.c.id.primary_key
    assert not table.c.asset_tag.nullable
    assert not table.c.type.nullable
    assert not table.c.serial_number.nullable
    assert not table.c.status.nullable
    assert table.c.assigned_to.nullable
    assert not table.c.purchase_date.nullable
    assert table.c.warranty_expiry.nullable
    assert table.c.notes.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable


def test_asset_unique_fields() -> None:
    table = Asset.__table__

    assert table.c.asset_tag.unique
    assert table.c.serial_number.unique


def test_asset_status_default() -> None:
    column = Asset.__table__.c.status

    assert column.server_default is not None


def test_asset_assigned_to_foreign_key() -> None:
    column = Asset.__table__.c.assigned_to

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "SET NULL"


def test_asset_indexes() -> None:
    table = Asset.__table__

    index_names = {index.name for index in table.indexes}

    assert "ix_assets_assigned_to" in index_names
    assert "ix_assets_status" in index_names
    assert "ix_assets_type" in index_names
    assert "ix_assets_warranty_expiry" in index_names


def test_asset_assignment_constraint() -> None:
    table = Asset.__table__

    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ck_assets_assignment_status" in constraint_names
