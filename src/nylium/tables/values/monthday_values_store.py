"""Month/day values store — read/write/clear a month/day cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.monthday_value import MonthDayValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class MonthDayValues(ScalarValuesTable[MonthDayValue]):
    """The monthday_values table as a store of writable month/day cells."""

    __row__: ClassVar[type[Row]] = MonthDayValue


monthday_values = MonthDayValues()
