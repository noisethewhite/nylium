"""MonthDayValues table store for MonthDayValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.month_day_value import MonthDayValue

class MonthDayValues(ScalarValuesTable[MonthDayValue]):
    """The monthday_values table as a store of writable monthday cells."""

    __row__: ClassVar[type[Row]] = MonthDayValue

monthday_values = MonthDayValues()
