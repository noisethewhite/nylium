"""PropUUID — typed identifier for a ``Prop`` row (``props``)."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pydantic_core import core_schema

import sqlalchemy as sqla
from sqlalchemy.orm import Mapped

from nylium.Constants import Constants
from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.database.Table import Row
from nylium.data.rows import (
    BooleanValue,
    DateValue,
    DatetimeValue,
    InstanceLink,
    IntegerValue,
    MonthDayTimeValue,
    MonthDayValue,
    NumericValue,
    Prop,
    StringValue,
    TimeValue,
)
from nylium.data.tables import props, trait_style, traits, types
from nylium.uuid.ObjectUUID import ObjectUUID


class _PropKeyedValues(Protocol):
    inst_uuid: Mapped[UUID]
    prop_uuid: Mapped[UUID]


# Tables keyed by prop_uuid — a retype wipes the old values from all of
# them so the new type starts clean (Null) on every instance.
_PROP_KEYED_VALUE_TABLES: tuple[type[_PropKeyedValues], ...] = (
    StringValue,
    IntegerValue,
    NumericValue,
    BooleanValue,
    DatetimeValue,
    DateValue,
    TimeValue,
    MonthDayValue,
    MonthDayTimeValue,
    InstanceLink,
)


class PropUUID(UUID):
    """A ``props`` uuid carrying its own table lookup and value purging."""

    @classmethod
    def of(cls, value: UUID) -> "PropUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> Prop | None:
        """The ``Prop`` row this uuid points at, or ``None`` if it is gone."""
        return props.get(self)

    def value_type_name(self) -> str:
        """The wire-facing value spec: the concrete type's name, or
        ``Any<TraitName>`` for a trait-bound prop (ADR-0013)."""
        prop = self.get()
        if prop is None:
            raise KeyError(f"Prop {self} does not exist")
        if prop.value_trait_uuid is not None:
            t = traits.get(prop.value_trait_uuid)
            if t is None:
                raise KeyError(f"Trait with UUID {prop.value_trait_uuid} does not exist")
            return f"Any<{t.name}>"
        if prop.value_type_uuid is None:
            raise KeyError(f"Prop {prop.key!r} has no value typing")
        t = types.get(prop.value_type_uuid)
        if t is None:
            raise KeyError(f"Type with UUID {prop.value_type_uuid} does not exist")
        return t.name

    def owner_trait(self) -> tuple[str, str] | None:
        """``(name, color)`` of the owning trait, None for a type-owned prop."""
        prop = self.get()
        if prop is None:
            raise KeyError(f"Prop {self} does not exist")
        if prop.owner_trait_uuid is None:
            return None
        t = traits.get(prop.owner_trait_uuid)
        if t is None:
            raise KeyError(f"Trait with UUID {prop.owner_trait_uuid} does not exist")
        return t.name, trait_style[t.uuid].color

    @Database.use_same_session
    def purge_values(self) -> None:
        """Wipe every stored value of this prop across all value tables."""
        for table in _PROP_KEYED_VALUE_TABLES:
            tc = get_mapper(table).columns
            _ = Database.execute(sqla.delete(table).where(tc.prop_uuid == self))
        Database.flush()

    @Database.use_same_session
    def purge_values_for_instances(self, inst_uuids: list[ObjectUUID]) -> None:
        """ADR-0013 detach: wipe this prop's values, but only on the given
        instances (the trait's other types keep theirs)."""
        if not inst_uuids:
            return
        for table in _PROP_KEYED_VALUE_TABLES:
            tc = get_mapper(table).columns
            _ = Database.execute(
                sqla.delete(table).where(
                    tc.prop_uuid == self,
                    tc.inst_uuid.in_(inst_uuids),
                )
            )
        Database.flush()

    @Database.use_same_session
    def collect_range(self, spec_name: str, lo: object, hi: object) -> list[ObjectUUID]:
        """Every instance whose value of this prop falls within [lo, hi].

        ``spec_name`` is the member prop's value spec (ordered scalar); it
        picks the matching value table."""
        if spec_name == Constants.Scalar.INTEGER:
            table: type[Row] = IntegerValue
        elif spec_name == Constants.Scalar.DATE:
            table = DateValue
        elif spec_name == Constants.Scalar.DATETIME:
            table = DatetimeValue
        else:
            # Numeric and Numeric<Unit> both store their magnitude in numeric_values
            table = NumericValue
        c = get_mapper(table).columns
        stmt = sqla.select(c.inst_uuid).where(
            c.prop_uuid == self,
            c.value >= lo,
            c.value <= hi,
        )
        rows: list[UUID] = list(Database.scalars(stmt).all())
        return [ObjectUUID.of(u) for u in rows]

    @Database.use_same_session
    def linked_uuids(self) -> list[UUID]:
        """Uuids of every instance linked through this prop, across all owners."""
        c = get_mapper(InstanceLink).columns
        return list(Database.scalars(sqla.select(c.uuid).where(c.prop_uuid == self)).all())

    @Database.use_same_session
    def read_with_unit(self, inst_uuid: UUID) -> tuple[Decimal, str | None] | None:
        """Stored (canonical magnitude, entered unit part name) pair, or None."""
        row = Database.get(NumericValue, (inst_uuid, self))
        if row is None:
            return None
        return row.value, row.unit

    @Database.use_same_session
    def write_with_unit(self, inst_uuid: UUID, value: Decimal, unit: str | None) -> None:
        """Upsert one numeric cell including the entered unit part name."""
        row = Database.get(NumericValue, (inst_uuid, self))
        if row is None:
            Database.add(
                NumericValue(inst_uuid=inst_uuid, prop_uuid=self, value=value, unit=unit)
            )
            return
        row.value = value
        row.unit = unit
