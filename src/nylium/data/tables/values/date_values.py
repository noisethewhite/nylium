"""DateValues table store for DateValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.data.tables.values.scalar_values_table import ScalarValuesTable
from nylium.data.rows.values.date_value import DateValue

class DateValues(ScalarValuesTable[DateValue]):
    """The date_values table as a store of writable date cells."""

    __row__: ClassVar[type[Row]] = DateValue

date_values = DateValues()
