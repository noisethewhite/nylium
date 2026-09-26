from __future__ import annotations
from nylium.database import Database
from decimal import Decimal
from nylium.data.tables import NumericValues
from nylium.ny.NyProp import NyProp
from nylium.ny.NyType import NyType
from nylium.data.types.Quantity import Quantity
from nylium.uuid import ObjectUUID, PropUUID
from nylium.server.ValidationError import ValidationError
from nylium.data.tables import unit_parts


class NyUnit:
    @classmethod
    def is_unit_numeric(cls, type_name: str) -> bool:
        """Semantic check (DB): the parameter must name a kind='unit' type."""
        unit_name = NyType.unit_param_of(type_name)
        if unit_name is None:
            return False
        owner = NyType.by_name(unit_name)
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
        part = next(
            (p for p in unit_parts.where(type_uuid=owner.uuid) if p.name == value.unit),
            None,
        )
        if part is None:
            raise ValidationError(
                f"{value.unit!r} is not a part of unit {owner.name!r}"
            )
        canonical = (value.value - cls._decimal(part.offset)) / cls._decimal(
            part.multiplier
        )
        return Quantity(value=canonical, unit=value.unit)

    @classmethod
    @Database.use_same_session
    def read(
        cls, inst_uuid: ObjectUUID, prop: NyProp, type_name: str
    ) -> Quantity | None:
        stored = PropUUID.of(prop.uuid).read_with_unit(inst_uuid)
        if stored is None:
            return None
        canonical, entered_unit = stored
        if entered_unit is None:
            return Quantity(value=canonical, unit=None)
        owner = cls._unit_owner(type_name)
        part = next(
            (
                p
                for p in unit_parts.where(type_uuid=owner.uuid)
                if p.name == entered_unit
            ),
            None,
        )
        if part is None:
            # delete-in-use is refused and renames propagate, so a missing
            # part means corrupted data — fail loud, never silently re-scale
            raise RuntimeError(
                f"stored value references unknown part {entered_unit!r} of unit {owner.name!r}"
            )
        display = canonical * cls._decimal(part.multiplier) + cls._decimal(part.offset)
        return Quantity(value=display, unit=entered_unit)

    @classmethod
    @Database.commit_after_this
    def write(
        cls, inst_uuid: ObjectUUID, prop: NyProp, quantity: Quantity | None
    ) -> None:
        if quantity is None:
            _ = NumericValues.clear(inst_uuid, prop.uuid)
            return
        PropUUID.of(prop.uuid).write_with_unit(inst_uuid, quantity.value, quantity.unit)

    # --- internals ---

    @classmethod
    def _unit_owner(cls, type_name: str) -> NyType:
        unit_name = NyType.unit_param_of(type_name)
        if unit_name is None:
            raise TypeError(f"{type_name!r} is not a unit numeric")
        owner = NyType.by_name(unit_name)
        if owner is None or not owner.is_unit:
            raise KeyError(f"no unit {unit_name!r}")
        return owner

    @staticmethod
    def _decimal(raw: object) -> Decimal:
        if not isinstance(raw, Decimal):
            raise RuntimeError(f"unit part factor {raw!r} is not a Decimal")
        return raw
