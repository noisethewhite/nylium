# Scalar prop-value cells (the nine *Values tables minus instance/array/
# file). ``ScalarCellsTable`` mirrors ``ScalarTable`` in the objects layer
# (``wscalar``); the alias stays here so the objects layer never names the
# table classes directly.
#
# ADR-0019: every scalar-cell statement lives behind the functions below.
from collections.abc import Callable
from typing import cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, use_same_session
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


@use_same_session
def read(table: type[ScalarCellsTable], inst_uuid: UUID, prop_uuid: UUID) -> object:
    """Raw stored value, or None when the cell is absent.

    Converting storage <-> python is the caller's job (``WScalar``.
    ``from_storage`` / ``to_storage``).
    """
    row = Database.get(table, (inst_uuid, prop_uuid))
    return None if row is None else row.value


@use_same_session
def write(
    table: type[ScalarCellsTable], inst_uuid: UUID, prop_uuid: UUID, value: object
) -> None:
    """Upsert one cell (insert or update in place)."""
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


@use_same_session
def clear(table: type[ScalarCellsTable], inst_uuid: UUID, prop_uuid: UUID) -> bool:
    """Delete the row if present (attribute deletion at the object layer).

    Returns True when a row was actually deleted — the object layer bumps
    modified_at only on a real delete.
    """
    row = Database.get(table, (inst_uuid, prop_uuid))
    if row is None:
        return False
    Database.delete(row)
    return True
