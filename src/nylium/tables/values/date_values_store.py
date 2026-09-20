"""Date values store — read/write/clear a date cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.date_value import DateValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class DateValues(ScalarValuesTable[DateValue]):
    """The date_values table as a store of writable date cells."""

    __row__: ClassVar[type[Row]] = DateValue


date_values = DateValues()
