"""IntegerValues table store for IntegerValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.integer_value import IntegerValue

class IntegerValues(ScalarValuesTable[IntegerValue]):
    """The integer_values table as a store of writable integer cells."""

    __row__: ClassVar[type[Row]] = IntegerValue

integer_values = IntegerValues()
