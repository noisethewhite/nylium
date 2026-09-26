"""Table stores for the *values tables.

Scalar value tables share one store shape — ``read``/``write``/``clear``
on ``ScalarValuesTable`` — and the concrete stores only pin their
``__row__``. The structural stores (``ArrayValues``, ``FileValues``,
``InstanceLinks``) used to carry their own query methods; those moved to
the typed uuid handles (``ArrayUUID`` / ``FileUUID`` / ``ObjectUUID`` /
``PropUUID``), so every store here is a pure row container.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Generic, TypeVar, cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.Row import Row, get_mapper
from nylium.database.Table import Table
from nylium.data.rows import (
    ArrayValue,
    BooleanValue,
    DateValue,
    DatetimeValue,
    FileValue,
    InstanceLink,
    IntegerValue,
    MonthDayTimeValue,
    MonthDayValue,
    NumericValue,
    StringValue,
    TimeValue,
)

_R = TypeVar("_R", bound=Row)


class ScalarValuesTable(Table[tuple[UUID, UUID], _R], Generic[_R]):
    """Shared store shape for the nine scalar value tables.

    ``read`` / ``write`` / ``clear`` operate on RAW storage values; the
    storage <-> python conversion stays with the ``NyScalar`` markers
    (``to_storage`` / ``from_storage``).
    """

    __row__: ClassVar[type[Row]]

    @classmethod
    def _table(cls) -> type[Row]:
        """The mapped class — the Row itself (no ``TABLE_*`` indirection)."""
        return cls.__row__

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: UUID, prop_uuid: UUID) -> object:
        """Raw stored value, or None when the cell is absent."""
        row = Database.get(cls._table(), (inst_uuid, prop_uuid))
        return None if row is None else getattr(row, "value")

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop_uuid: UUID, value: object) -> None:
        """Upsert one cell (insert or update in place)."""
        table = cls._table()
        row = Database.get(table, (inst_uuid, prop_uuid))
        if row is None:
            ctor = cast("Callable[..., Row]", table)
            Database.add(ctor(inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value))
            return
        columns = get_mapper(table).columns
        _ = Database.execute(
            sqla.update(table)
            .where(columns.inst_uuid == inst_uuid, columns.prop_uuid == prop_uuid)
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


class BooleanValues(ScalarValuesTable[BooleanValue]):
    __row__: ClassVar[type[Row]] = BooleanValue


class DateValues(ScalarValuesTable[DateValue]):
    __row__: ClassVar[type[Row]] = DateValue


class DatetimeValues(ScalarValuesTable[DatetimeValue]):
    __row__: ClassVar[type[Row]] = DatetimeValue


class IntegerValues(ScalarValuesTable[IntegerValue]):
    __row__: ClassVar[type[Row]] = IntegerValue


class MonthDayTimeValues(ScalarValuesTable[MonthDayTimeValue]):
    __row__: ClassVar[type[Row]] = MonthDayTimeValue


class MonthDayValues(ScalarValuesTable[MonthDayValue]):
    __row__: ClassVar[type[Row]] = MonthDayValue


class NumericValues(ScalarValuesTable[NumericValue]):
    __row__: ClassVar[type[Row]] = NumericValue


class StringValues(ScalarValuesTable[StringValue]):
    __row__: ClassVar[type[Row]] = StringValue


class TimeValues(ScalarValuesTable[TimeValue]):
    __row__: ClassVar[type[Row]] = TimeValue


class ArrayValues(Table[tuple[UUID, int], ArrayValue]):
    __row__: ClassVar[type[Row]] = ArrayValue


class FileValues(Table[tuple[UUID, UUID], FileValue]):
    __row__: ClassVar[type[Row]] = FileValue


class InstanceLinks(Table[tuple[UUID, UUID], InstanceLink]):
    __row__: ClassVar[type[Row]] = InstanceLink


boolean_values = BooleanValues()
date_values = DateValues()
datetime_values = DatetimeValues()
integer_values = IntegerValues()
monthdaytime_values = MonthDayTimeValues()
monthday_values = MonthDayValues()
numeric_values = NumericValues()
string_values = StringValues()
time_values = TimeValues()
array_values = ArrayValues()
file_values = FileValues()
instance_links = InstanceLinks()
