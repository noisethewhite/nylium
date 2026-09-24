"""MonthDayValues table store for MonthDayValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.Table import Row
from nylium.data.tables.values.ScalarValuesTable import ScalarValuesTable
from nylium.data.rows import MonthDayValue

class MonthDayValues(ScalarValuesTable[MonthDayValue]):
    """The monthday_values table as a store of writable monthday cells."""

    __row__: ClassVar[type[Row]] = MonthDayValue

monthday_values = MonthDayValues()
