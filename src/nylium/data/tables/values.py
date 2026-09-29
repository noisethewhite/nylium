"""Table stores for the *values tables.

Scalar value tables share one store shape — ``read``/``write``/``clear``
on ``ScalarValuesTable`` — and the concrete stores only pin their
``__row__``. The structural stores (``ArrayValues``, ``FileValues``,
``InstanceLinks``) used to carry their own query methods; those moved to
the typed uuid handles (``ArrayRef`` / ``FileRef`` / ``ObjectRef`` /
``PropRef``), so every store here is a pure row container.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.abc import ScalarValuesTable
from nylium.database import Row
from nylium.database import Table
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
