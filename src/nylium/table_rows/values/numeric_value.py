"""The numeric_values table: NumericValue (mapped Row) + NumericValues (store)."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class NumericValue(Row):
    __tablename__: ClassVar[str] = "numeric_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[Decimal] = mapped_column(nullable=False)
    # unit part name as entered (for `Numeric<Unit>` props); NULL means
    # the unit's base part or a plain unitless Numeric
    unit: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


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
