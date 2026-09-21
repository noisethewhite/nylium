"""ArrayValue mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.row import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class ArrayValue(Row):
    __tablename__: ClassVar[str] = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(nullable=False)
