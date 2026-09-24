"""DatetimeValues table store for DatetimeValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.Table import Row
from nylium.data.tables.values.ScalarValuesTable import ScalarValuesTable
from nylium.data.rows import DatetimeValue

class DatetimeValues(ScalarValuesTable[DatetimeValue]):
    """The datetime_values table as a store of writable datetime cells."""

    __row__: ClassVar[type[Row]] = DatetimeValue

datetime_values = DatetimeValues()
