from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_NumericValues:
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


# ADR-0019: unit-aware cell statements for `Numeric<Unit>` props — the
# generic cells helpers cover `value` only, the `unit` column lives here.
@Database.use_same_session
def read_with_unit(inst_uuid: UUID, prop_uuid: UUID) -> tuple[Decimal, str | None] | None:
    """Stored (canonical magnitude, entered unit part name) pair, or None."""
    row = Database.get(TABLE_NumericValues, (inst_uuid, prop_uuid))
    if row is None:
        return None
    return row.value, row.unit


@Database.use_same_session
def write_with_unit(
    inst_uuid: UUID, prop_uuid: UUID, value: Decimal, unit: str | None
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
