"""Scalar cell wrappers — the value-side read/write/clear statements for
the nine scalar ``*Values`` tables (excluding instance/array/file links).

This is a verbatim port of the former ``tables.values.cells`` functions:
each subclass owns one storage table (``TABLE``) and the cell statements
that used to take the table as a free parameter now read it off ``cls``.

The wrappers operate on RAW storage values; storage <-> python conversion
stays with the ``WScalar`` markers in the objects layer (``to_storage`` /
``from_storage``). A scalar marker reaches its wrapper through
``WScalar.SCALAR`` — that mapping is the ADR-0030 ``TABLE <-> scalars`` link.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.tables.values.boolean_values import TABLE_BooleanValues
from nylium.tables.values.date_values import TABLE_DateValues
from nylium.tables.values.datetime_values import TABLE_DatetimeValues
from nylium.tables.values.integer_values import TABLE_IntegerValues
from nylium.tables.values.monthday_values import TABLE_MonthDayValues
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues
from nylium.tables.values.numeric_values import TABLE_NumericValues
from nylium.tables.values.string_values import TABLE_StringValues
from nylium.tables.values.time_values import TABLE_TimeValues

ScalarCellsTable = (
    TABLE_StringValues
    | TABLE_IntegerValues
    | TABLE_NumericValues
    | TABLE_BooleanValues
    | TABLE_DatetimeValues
    | TABLE_DateValues
    | TABLE_TimeValues
    | TABLE_MonthDayValues
    | TABLE_MonthDayTimeValues
)


class Scalar:
    """Base scalar cell wrapper. ``TABLE`` is the mapped ``*Values`` class."""

    TABLE: ClassVar[type[ScalarCellsTable]]

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: UUID, prop_uuid: UUID) -> object:
        """Raw stored value, or None when the cell is absent."""
        row = Database.get(cls.TABLE, (inst_uuid, prop_uuid))
        return None if row is None else row.value

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop_uuid: UUID, value: object) -> None:
        """Upsert one cell (insert or update in place)."""
        row = Database.get(cls.TABLE, (inst_uuid, prop_uuid))
        if row is None:
            ctor = cast("Callable[..., ScalarCellsTable]", cls.TABLE)
            Database.add(ctor(inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value))
            return
        _ = Database.execute(
            sqla.update(cls.TABLE)
            .where(cls.TABLE.inst_uuid == inst_uuid, cls.TABLE.prop_uuid == prop_uuid)
            .values(value=value)
        )

    @classmethod
    @Database.use_same_session
    def clear(cls, inst_uuid: UUID, prop_uuid: UUID) -> bool:
        """Delete the row if present; True when a row was actually deleted."""
        row = Database.get(cls.TABLE, (inst_uuid, prop_uuid))
        if row is None:
            return False
        Database.delete(row)
        return True
