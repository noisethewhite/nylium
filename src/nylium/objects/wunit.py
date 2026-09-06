"""WUnit: persistence of a `Numeric<Unit>` prop — one numeric_values row
storing the canonical (base-part) magnitude in `value` and the part name
as entered in `unit`.

A bare `Numeric` prop never reaches this facade: `WType.unit_param_of`
is None for it and WObject dispatches to the plain scalar path. The
unitless case of a unit numeric is a Quantity with `unit=None`, stored
with NULL unit — magnitude is canonical by definition.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from nylium.database import Database, databasemethod
from nylium.tables import NumericValues, UnitParts
from nylium.objects.quantity import Quantity
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType
from nylium.server.errors import ValidationError


class WUnit:
    @classmethod
    def is_unit_numeric(cls, type_name: str) -> bool:
        """Semantic check (DB): the parameter must name a kind='unit' type."""
        unit_name = WType.unit_param_of(type_name)
        if unit_name is None:
            return False
        owner = WType.by_name(unit_name)
        return owner is not None and owner.is_unit

    @classmethod
    def validate(cls, type_name: str, value: object) -> Quantity | None:
        """None unsets the prop. A Quantity is checked against the unit's
        parts and converted to the canonical magnitude; the returned
        Quantity keeps the entered part name for storage."""
        if value is None:
            return None
        if not isinstance(value, Quantity):
            raise TypeError(
                f"{type_name} takes Quantity, got {type(value).__name__}"
            )
        owner = cls._unit_owner(type_name)
        if value.unit is None:
            return Quantity(value=value.value, unit=None)
        part = UnitParts.by_name(owner.uuid, value.unit)
        if part is None:
            raise ValidationError(
                f"{value.unit!r} is not a part of unit {owner.name!r}"
            )
        canonical = (value.value - cls._decimal(part.offset)) / cls._decimal(
            part.multiplier
        )
        return Quantity(value=canonical, unit=value.unit)

    @classmethod
    @databasemethod(commit=False)
    def read(
        cls, inst_uuid: UUID, prop: WProp, type_name: str
    ) -> Quantity | None:
        row = Database.session.get(NumericValues, (inst_uuid, prop.uuid))
        if row is None:
            return None
        canonical = row.value
        entered_unit = row.unit
        if entered_unit is None:
            return Quantity(value=canonical, unit=None)
        owner = cls._unit_owner(type_name)
        part = UnitParts.by_name(owner.uuid, entered_unit)
        if part is None:
            # delete-in-use is refused and renames propagate, so a missing
            # part means corrupted data — fail loud, never silently re-scale
            raise RuntimeError(
                f"stored value references unknown part {entered_unit!r} of unit {owner.name!r}"
            )
        display = canonical * cls._decimal(part.multiplier) + cls._decimal(part.offset)
        return Quantity(value=display, unit=entered_unit)

    @classmethod
    @databasemethod(commit=True)
    def write(
        cls, inst_uuid: UUID, prop: WProp, quantity: Quantity | None
    ) -> None:
        if quantity is None:
            row = Database.session.get(NumericValues, (inst_uuid, prop.uuid))
            if row is not None:
                Database.session.delete(row)
            return
        row = Database.session.get(NumericValues, (inst_uuid, prop.uuid))
        if row is None:
            Database.session.add(
                NumericValues(
                    inst_uuid=inst_uuid,
                    prop_uuid=prop.uuid,
                    value=quantity.value,
                    unit=quantity.unit,
                )
            )
            return
        row.value = quantity.value
        row.unit = quantity.unit

    # --- internals ---

    @classmethod
    def _unit_owner(cls, type_name: str) -> WType:
        unit_name = WType.unit_param_of(type_name)
        if unit_name is None:
            raise TypeError(f"{type_name!r} is not a unit numeric")
        owner = WType.by_name(unit_name)
        if owner is None or not owner.is_unit:
            raise KeyError(f"no unit {unit_name!r}")
        return owner

    @staticmethod
    def _decimal(raw: object) -> Decimal:
        if not isinstance(raw, Decimal):
            raise RuntimeError(f"unit part factor {raw!r} is not a Decimal")
        return raw
