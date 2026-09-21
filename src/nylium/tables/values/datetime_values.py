"""DatetimeValues table store for DatetimeValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.datetime_value import DatetimeValue

class DatetimeValues(ScalarValuesTable[DatetimeValue]):
    """The datetime_values table as a store of writable datetime cells."""

    __row__: ClassVar[type[Row]] = DatetimeValue

datetime_values = DatetimeValues()
