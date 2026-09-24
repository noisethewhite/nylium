"""Color scalar (ADR-0005): a first-class 3-byte RGB hex scalar, the
backing type of type/tag colors. Types.color stores only hex — the legacy
named palette is migrated away and rejected at the API boundary."""

import pytest

from nylium.api import Api, ScalarValue
from nylium.objects import NyScalar
from nylium.objects.navigation import type_color, type_icon
from nylium.objects.NyColor import NyColor
from nylium.server import NyliumApp
from nylium.server.ValidationError import ValidationError
from sqlalchemy import text
from nylium.database import Database


def test_color_is_a_registered_builtin():
    _ = Api.create_type("T", {"name": "String"}, "Ts")  # seeds builtins
    view = Api.get_type("Color")
    assert view is not None
    assert (type_icon(view.uuid), type_color(view.uuid)) == ("palette", NyColor.DEFAULT)


@pytest.mark.parametrize(
    "value",
    ["#9e9e9e", "#FFFFFF", "#00ab0F"],
)
def test_validate_accepts_hex(value):
    NyScalar.validate("Color", value)


@pytest.mark.parametrize(
    "value",
    ["9e9e9e", "#9e9e9", "#9e9e9e9", "#gg0000", "red", ""],
)
def test_validate_rejects_non_hex(value):
    with pytest.raises(ValueError):
        NyScalar.validate("Color", value)


def test_validate_rejects_non_string():
    with pytest.raises(TypeError):
        NyScalar.validate("Color", 0x9E9E9E)


def test_color_prop_roundtrip_through_write_path():
    _ = Api.create_type("Swatch", {"name": "String", "accent": "Color"}, "Swatches")
    swatch = Api.create_object("Swatch", {"name": "hot", "accent": "#ff00aa"})
    reloaded = Api.get_object(swatch.uuid)
    assert reloaded is not None
    accent = reloaded.props["accent"]
    assert isinstance(accent, ScalarValue)
    assert accent.value == "#ff00aa"
    with pytest.raises(ValueError):
        Api.create_object("Swatch", {"name": "bad", "accent": "hotpink"})


@pytest.mark.parametrize(
    "create",
    [
        lambda: Api.create_type("T", {"name": "String"}, "Ts", color="red"),
        lambda: Api.create_enum("E", ["a"], color="gray"),
        lambda: Api.create_unit("U", "u", color="blue"),
        lambda: Api.rename_type("String", color="teal"),
    ],
)
def test_named_palette_rejected_at_api_boundary(create):
    _ = Api.create_type("Seed", {"name": "String"}, "Seeds")  # seeds builtins
    with pytest.raises(ValidationError):
        create()


def test_legacy_named_colors_migrate_to_hex():


    _ = Api.create_type("Old", {"name": "String"}, "Olds", color="#123456")
    # simulate a pre-ADR-0014 database: decor row absent, legacy columns
    # back on types with a named-palette color planted on "Old"
    with Database.engine.begin() as connection:
        _ = connection.execute(
            text("DELETE FROM type_decor WHERE uuid IN (SELECT uuid FROM types WHERE name = 'Old')")
        )
        _ = connection.execute(text("ALTER TABLE types ADD COLUMN plural_name TEXT"))
        _ = connection.execute(text("ALTER TABLE types ADD COLUMN icon TEXT"))
        _ = connection.execute(text("ALTER TABLE types ADD COLUMN color TEXT"))
        _ = connection.execute(
            text("UPDATE types SET plural_name = name || 's', icon = 'inventory_2', color = '#9e9e9e'")
        )
        _ = connection.execute(text("UPDATE types SET color = 'red' WHERE name = 'Old'"))

    NyliumApp._migrate_schema()

    migrated = Api.get_type("Old")
    assert migrated is not None
    assert type_color(migrated.uuid) == NyColor.LEGACY_PALETTE["red"]

    # idempotent — a second run leaves hex values alone
    NyliumApp._migrate_schema()
    again = Api.get_type("Old")
    assert again is not None
    assert type_color(again.uuid) == NyColor.LEGACY_PALETTE["red"]
