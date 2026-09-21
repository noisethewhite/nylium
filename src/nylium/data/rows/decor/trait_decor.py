"""TraitDecor mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class TraitDecor(Row):
    __tablename__: ClassVar[str] = "trait_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    color: Mapped[str] = mapped_column(Text, nullable=False)
