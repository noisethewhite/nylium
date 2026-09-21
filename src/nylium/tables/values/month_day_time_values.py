"""MonthDayTimeValues table store for MonthDayTimeValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.month_day_time_value import MonthDayTimeValue

class MonthDayTimeValues(ScalarValuesTable[MonthDayTimeValue]):
    """The monthdaytime_values table as a store of writable monthdaytime cells."""

    __row__: ClassVar[type[Row]] = MonthDayTimeValue

monthdaytime_values = MonthDayTimeValues()
