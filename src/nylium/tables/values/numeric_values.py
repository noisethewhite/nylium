"""NumericValues table store for NumericValue."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row
from nylium.tables.values.scalar_values_table import ScalarValuesTable
from nylium.rows.values.numeric_value import NumericValue

class NumericValues(ScalarValuesTable[NumericValue]):
    """The numeric_values table as a store of writable numeric cells."""

    __row__: ClassVar[type[Row]] = NumericValue

    @classmethod
    @Database.use_same_session
    def read_with_unit(
        cls, inst_uuid: UUID, prop_uuid: UUID
    ) -> tuple[Decimal, str | None] | None:
        """Stored (canonical magnitude, entered unit part name) pair, or None."""
        row = Database.get(NumericValue, (inst_uuid, prop_uuid))
        if row is None:
            return None
        return row.value, row.unit

    @classmethod
    @Database.use_same_session
    def write_with_unit(
        cls, inst_uuid: UUID, prop_uuid: UUID, value: Decimal, unit: str | None
    ) -> None:
        """Upsert one numeric cell including the entered unit part name."""
        row = Database.get(NumericValue, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                NumericValue(inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value, unit=unit)
            )
            return
        row.value = value
        row.unit = unit

numeric_values = NumericValues()
