"""Datetime values store — read/write/clear a datetime cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.datetime_value import DatetimeValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class DatetimeValues(ScalarValuesTable[DatetimeValue]):
    """The datetime_values table as a store of writable datetime cells."""

    __row__: ClassVar[type[Row]] = DatetimeValue


datetime_values = DatetimeValues()
