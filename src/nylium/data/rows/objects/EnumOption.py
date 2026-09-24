"""EnumOption mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class EnumOption(Row):
    __tablename__: ClassVar[str] = "enum_options"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint("type_uuid", "value"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
