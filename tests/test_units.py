"""User-defined units: kind='unit' types, part CRUD with propagation,
membership and conversion on write/read. Api-level; HTTP shape lives in
test_http.py."""
from decimal import Decimal

import pytest

from nylium.api import Api, ScalarValue, TypeView
from nylium.objects.quantity import Quantity
from nylium.server.errors import ValidationError


def temperature_unit() -> TypeView:
    return Api.create_unit(
        "Temperature", "°C", [("°F", Decimal("1.8"), Decimal(32))]
    )


def mass_unit() -> TypeView:
    return Api.create_unit("Mass", "g", [("kg", Decimal("1000"), Decimal(0))])


def oven_type() -> TypeView:
    return Api.create_type(
        "Oven",
        {"name": "String", "temp": "Numeric<Temperature>"},
        "Ovens",
    )


def _part_uuids(view: TypeView) -> dict[str, object]:
    return {part.name: part.uuid for part in view.unit_parts}


def test_create_unit_view():
    view = temperature_unit()
    assert view.kind == "unit"
    assert view.props == []
    assert [(p.name, p.multiplier, p.offset, p.is_base) for p in view.unit_parts] == [
        ("°C", Decimal(1), Decimal(0), True),
        ("°F", Decimal("1.8"), Decimal(32), False),
    ]


def test_unit_guards():
    with pytest.raises(ValidationError):
        Api.create_unit("  ", "kg")
    with pytest.raises(ValidationError):
        Api.create_unit("Mass", "  ")
    with pytest.raises(ValidationError):
        # a secondary duplicating the base name
        Api.create_unit("Mass", "g", [("g", Decimal(1), Decimal(0))])
    with pytest.raises(ValidationError):
        Api.create_unit("Mass", "g", [("kg", Decimal(0), Decimal(0))])


def test_unit_write_converts_and_read_displays():
    _ = temperature_unit()
    _ = oven_type()
    oven = Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(32), "°F")})
    # canonical 0°C is stored; the view renders back the magnitude as entered
    assert oven.props["temp"] == ScalarValue(value=Decimal(32), unit="°F")
    reloaded = Api.get_object(oven.uuid)
    assert reloaded is not None
    assert reloaded.props["temp"] == ScalarValue(value=Decimal(32), unit="°F")


def test_unit_base_write_is_identity():
    _ = mass_unit()
    _ = Api.create_type(
        "Bag", {"name": "String", "weight": "Numeric<Mass>"}, "Bags"
    )
    bag = Api.create_object("Bag", {"name": "b1", "weight": Quantity(Decimal(500), None)})
    assert bag.props["weight"] == ScalarValue(value=Decimal(500), unit=None)


def test_unit_part_membership():
    _ = temperature_unit()
    _ = oven_type()
    with pytest.raises(ValidationError):
        Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(1), "kelvin")})


def test_unit_prop_requires_existing_unit():
    with pytest.raises(ValidationError):
        Api.create_type("Bad", {"name": "String", "x": "Numeric<Nope>"}, "Bads")
    # a bare unit name is not a prop type — the parameter is mandatory
    _ = temperature_unit()
    with pytest.raises(ValidationError):
        Api.create_type("Bad2", {"name": "String", "x": "Temperature"}, "Bad2s")


def test_sync_parts_rename_propagates():
    view = temperature_unit()
    _ = oven_type()
    oven = Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(32), "°F")})
    uuids = _part_uuids(view)
    synced = Api.sync_unit_parts(
        "Temperature",
        [
            (uuids["°C"], "°C", Decimal(1), Decimal(0), True),  # type: ignore[list-item]
            (uuids["°F"], "fahrenheit", Decimal("1.8"), Decimal(32), False),  # type: ignore[list-item]
        ],
    )
    assert [p.name for p in synced.unit_parts] == ["°C", "fahrenheit"]
    reloaded = Api.get_object(oven.uuid)
    assert reloaded is not None
    assert reloaded.props["temp"] == ScalarValue(value=Decimal(32), unit="fahrenheit")


def test_sync_parts_delete_in_use_refused():
    view = temperature_unit()
    _ = oven_type()
    _ = Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(32), "°F")})
    uuids = _part_uuids(view)
    with pytest.raises(ValueError):
        Api.sync_unit_parts(
            "Temperature",
            [(uuids["°C"], "°C", Decimal(1), Decimal(0), True)],  # type: ignore[list-item]
        )


def test_sync_parts_base_switch_refused_with_values():
    view = temperature_unit()
    _ = oven_type()
    _ = Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(0), "°C")})
    uuids = _part_uuids(view)
    with pytest.raises(ValidationError):
        Api.sync_unit_parts(
            "Temperature",
            [
                (uuids["°C"], "°C", Decimal(1), Decimal(0), False),  # type: ignore[list-item]
                (uuids["°F"], "°F", Decimal("1.8"), Decimal(32), True),  # type: ignore[list-item]
            ],
        )


def test_sync_parts_validation():
    view = temperature_unit()
    uuids = _part_uuids(view)
    # not exactly one base
    with pytest.raises(ValidationError):
        Api.sync_unit_parts(
            "Temperature",
            [
                (uuids["°C"], "°C", Decimal(1), Decimal(0), True),  # type: ignore[list-item]
                (uuids["°F"], "°F", Decimal("1.8"), Decimal(32), True),  # type: ignore[list-item]
            ],
        )
    # non-identity base
    with pytest.raises(ValidationError):
        Api.sync_unit_parts(
            "Temperature",
            [
                (uuids["°C"], "°C", Decimal(2), Decimal(0), True),  # type: ignore[list-item]
                (uuids["°F"], "°F", Decimal("1.8"), Decimal(32), False),  # type: ignore[list-item]
            ],
        )
    with pytest.raises(KeyError):
        Api.sync_unit_parts("NoSuchUnit", [])
    _ = Api.create_type("Plain", {"name": "String"}, "Plains")
    with pytest.raises(ValidationError):
        Api.sync_unit_parts("Plain", [])


def test_unit_rename_tows_parameterized_row():
    _ = temperature_unit()
    _ = oven_type()
    renamed = Api.rename_type("Temperature", "Heat")
    assert renamed.name == "Heat" and renamed.kind == "unit"
    assert Api.get_type("Temperature") is None
    assert Api.get_type("Numeric<Heat>") is not None
    oven = Api.create_object("Oven", {"name": "o1", "temp": Quantity(Decimal(32), "°F")})
    assert oven.props["temp"] == ScalarValue(value=Decimal(32), unit="°F")


def test_unit_delete_guard():
    _ = temperature_unit()
    _ = oven_type()
    with pytest.raises(ValueError):
        Api.delete_type("Temperature")
    # deleting the owner type frees the unit
    assert Api.delete_type("Oven")
    assert Api.delete_type("Temperature")
    assert Api.get_type("Numeric<Temperature>") is None
