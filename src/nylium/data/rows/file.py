"""File mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class File(Row):
    __tablename__: ClassVar[str] = "files"

    uuid: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, kw_only=True
    )
    type_name: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
