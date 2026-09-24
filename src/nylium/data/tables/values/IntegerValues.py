"""IntegerValues table store for IntegerValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.Table import Row
from nylium.data.tables.values.ScalarValuesTable import ScalarValuesTable
from nylium.data.rows import IntegerValue

class IntegerValues(ScalarValuesTable[IntegerValue]):
    """The integer_values table as a store of writable integer cells."""

    __row__: ClassVar[type[Row]] = IntegerValue

integer_values = IntegerValues()
