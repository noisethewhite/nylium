"""UnitPart mapped row."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class UnitPart(Row):
    __tablename__: ClassVar[str] = "unit_parts"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint("type_uuid", "name"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    offset: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
