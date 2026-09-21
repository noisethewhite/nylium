"""TimeValues table store for TimeValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.time_value import TimeValue

class TimeValues(ScalarValuesTable[TimeValue]):
    """The time_values table as a store of writable time cells."""

    __row__: ClassVar[type[Row]] = TimeValue

time_values = TimeValues()
