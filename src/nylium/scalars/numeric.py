"""Numeric cell wrapper — TABLE_NumericValues, incl. unit-aware cells."""
from __future__ import annotations

from decimal import Decimal
from typing import final
from uuid import UUID

from nylium.database import Database
from nylium.scalars.base import Scalar
from nylium.tables.values.numeric_values import TABLE_NumericValues


@final
class Numeric(Scalar):
    TABLE = TABLE_NumericValues

    @classmethod
    @Database.use_same_session
    def read_with_unit(
        cls, inst_uuid: UUID, prop_uuid: UUID
    ) -> tuple[Decimal, str | None] | None:
        """Stored (canonical magnitude, entered unit part name) pair, or None."""
        row = Database.get(TABLE_NumericValues, (inst_uuid, prop_uuid))
        if row is None:
            return None
        return row.value, row.unit

    @classmethod
    @Database.use_same_session
    def write_with_unit(
        cls, inst_uuid: UUID, prop_uuid: UUID, value: Decimal, unit: str | None
    ) -> None:
        """Upsert one numeric cell including the entered unit part name."""
        row = Database.get(TABLE_NumericValues, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                TABLE_NumericValues(
                    inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value, unit=unit
                )
            )
            return
        row.value = value
        row.unit = unit
