"""String values store — read/write/clear a string cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.tables.values.scalar_values import ScalarValuesTable
from nylium.rows.values.string_value import StringValue


class StringValues(ScalarValuesTable[StringValue]):
    """The string_values table as a store of writable string cells."""

    __row__: ClassVar[type[Row]] = StringValue


string_values = StringValues()
