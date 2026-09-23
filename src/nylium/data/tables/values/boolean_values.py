"""BooleanValues table store for BooleanValue."""
from __future__ import annotations

from typing import ClassVar
from nylium.database.table import Row
from nylium.data.tables.values.scalar_values_table import ScalarValuesTable
from nylium.data.rows import BooleanValue

class BooleanValues(ScalarValuesTable[BooleanValue]):
    """The boolean_values table as a store of writable boolean cells."""

    __row__: ClassVar[type[Row]] = BooleanValue

boolean_values = BooleanValues()
