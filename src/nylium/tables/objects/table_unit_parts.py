"""Parts of a user-defined unit type (raw row mapping).

A unit is a `types` row with kind='unit': the base part plus secondary
parts with an affine conversion factor (`base = (entered - offset) /
multiplier`, so 32°F at 1.8/32 is 0°C). Numeric props parameterize on the
unit as `Numeric<Temperature>`; stored values live in numeric_values —
canonical magnitude in `value`, the part name as entered in `unit`.
"""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_UnitParts:
    __tablename__: ClassVar[str] = "unit_parts"
    __table_args__: ClassVar[tuple[object, ...]] = (
        # Part names are unique within their unit — values reference them
        # by (prop type, part name), so ambiguity would corrupt reads
        UniqueConstraint("type_uuid", "name"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # affine conversion entered -> base: base = (entered - offset) / multiplier
    multiplier: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    offset: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    # exactly one part per unit is the base (identity conversion: 1/0)
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
