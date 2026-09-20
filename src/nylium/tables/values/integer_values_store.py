"""Integer values store — read/write/clear an integer cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.integer_value import IntegerValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class IntegerValues(ScalarValuesTable[IntegerValue]):
    """The integer_values table as a store of writable integer cells."""

    __row__: ClassVar[type[Row]] = IntegerValue


integer_values = IntegerValues()
