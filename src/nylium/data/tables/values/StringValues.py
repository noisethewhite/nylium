"""StringValues table store for StringValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.Table import Row
from nylium.data.tables.values.ScalarValuesTable import ScalarValuesTable
from nylium.data.rows import StringValue

class StringValues(ScalarValuesTable[StringValue]):
    """The string_values table as a store of writable string cells."""

    __row__: ClassVar[type[Row]] = StringValue

string_values = StringValues()
