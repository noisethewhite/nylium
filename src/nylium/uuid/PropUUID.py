"""PropUUID — typed identifier for a ``Prop`` row (``props``)."""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy.orm import Mapped

from nylium.Constants import Constants
from nylium.database import Database
from nylium.database.Row import mapper
from nylium.database.Table import Row
from nylium.data.rows import (
    BooleanValue,
    DateValue,
    DatetimeValue,
    InstanceValue,
    IntegerValue,
    MonthDayTimeValue,
    MonthDayValue,
    NumericValue,
    Prop,
    StringValue,
    TimeValue,
)
from nylium.data.tables import props
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
    InstanceValue,
)


class PropUUID(UUID):
    """A ``props`` uuid carrying its own table lookup and value purging."""

    @classmethod
    def of(cls, value: UUID) -> "PropUUID":
        return cls(str(value))

    def get(self) -> Prop | None:
        """The ``Prop`` row this uuid points at, or ``None`` if it is gone."""
        return props.get(self)

    @Database.use_same_session
    def purge_values(self) -> None:
        """Wipe every stored value of this prop across all value tables."""
        for table in _PROP_KEYED_VALUE_TABLES:
            tc = mapper(table).columns
            _ = Database.execute(sqla.delete(table).where(tc.prop_uuid == self))
        Database.flush()

    @Database.use_same_session
    def purge_values_for_instances(self, inst_uuids: list[ObjectUUID]) -> None:
        """ADR-0013 detach: wipe this prop's values, but only on the given
        instances (the trait's other types keep theirs)."""
        if not inst_uuids:
            return
        for table in _PROP_KEYED_VALUE_TABLES:
            tc = mapper(table).columns
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
        c = mapper(table).columns
        stmt = sqla.select(c.inst_uuid).where(
            c.prop_uuid == self,
            c.value >= lo,
            c.value <= hi,
        )
        rows: list[UUID] = list(Database.scalars(stmt).all())
        return [ObjectUUID.of(u) for u in rows]
