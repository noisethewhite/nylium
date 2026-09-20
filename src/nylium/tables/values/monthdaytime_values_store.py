"""Month/day+time values store — read/write/clear a month/day+time cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.monthdaytime_value import MonthDayTimeValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class MonthDayTimeValues(ScalarValuesTable[MonthDayTimeValue]):
    """The monthdaytime_values table as a store of writable month/day+time cells."""

    __row__: ClassVar[type[Row]] = MonthDayTimeValue


monthdaytime_values = MonthDayTimeValues()
