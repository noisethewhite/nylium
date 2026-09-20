"""Boolean values store — read/write/clear a boolean cell (ADR-0031)."""
from __future__ import annotations

from typing import ClassVar

from nylium.database.table import Row
from nylium.rows.values.boolean_value import BooleanValue
from nylium.tables.values.scalar_values import ScalarValuesTable


class BooleanValues(ScalarValuesTable[BooleanValue]):
    """The boolean_values table as a store of writable boolean cells."""

    __row__: ClassVar[type[Row]] = BooleanValue


boolean_values = BooleanValues()
