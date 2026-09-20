"""Generic value-side read/write/clear for the nine scalar ``*Values``
tables (ADR-0031): one shared store base, nine thin subclasses.

Composite PK ``(inst_uuid, prop_uuid)``. Writes go through explicit
insert/update because ``Row.persist`` stays single-PK-only. Each
``WScalar`` marker binds ``SCALAR`` to its store subclass; each store
subclass binds ``__row__`` to its snapshot Row.

This module imports no ``nylium.objects`` code — the objects layer
reaches down into the stores, never the reverse.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Generic, TypeVar, cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
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

_R = TypeVar("_R", bound=Row)


class ScalarValuesTable(Table[tuple[UUID, UUID], _R], Generic[_R]):
    """Shared store shape for the nine scalar value tables.

    ``read`` / ``write`` / ``clear`` operate on RAW storage values; the
    storage <-> python conversion stays with the ``WScalar`` markers
    (``to_storage`` / ``from_storage``).
    """

    __row__: ClassVar[type[Row]]

    @classmethod
    def _table(cls) -> type[ScalarCellsTable]:
        return cast("type[ScalarCellsTable]", cls.__row__.__table__)

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: UUID, prop_uuid: UUID) -> object:
        """Raw stored value, or None when the cell is absent."""
        row = Database.get(cls._table(), (inst_uuid, prop_uuid))
        return None if row is None else row.value

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop_uuid: UUID, value: object) -> None:
        """Upsert one cell (insert or update in place)."""
        table = cls._table()
        row = Database.get(table, (inst_uuid, prop_uuid))
        if row is None:
            ctor = cast("Callable[..., ScalarCellsTable]", table)
            Database.add(ctor(inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value))
            return
        _ = Database.execute(
            sqla.update(table)
            .where(table.inst_uuid == inst_uuid, table.prop_uuid == prop_uuid)
            .values(value=value)
        )

    @classmethod
    @Database.use_same_session
    def clear(cls, inst_uuid: UUID, prop_uuid: UUID) -> bool:
        """Delete the row if present; True when a row was actually deleted."""
        row = Database.get(cls._table(), (inst_uuid, prop_uuid))
        if row is None:
            return False
        Database.delete(row)
        return True
