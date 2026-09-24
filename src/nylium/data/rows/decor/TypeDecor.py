"""TypeDecor mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class TypeDecor(Row):
    __tablename__: ClassVar[str] = "type_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )
