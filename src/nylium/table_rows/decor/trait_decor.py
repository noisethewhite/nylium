"""The trait_decor table: TraitDecor (mapped Row) + TraitDecors (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TraitDecor(Row):
    __tablename__: ClassVar[str] = "trait_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    color: Mapped[str] = mapped_column(Text, nullable=False)


class TraitDecors(Table[UUID, TraitDecor]):
    """The trait_decor table as a Mapping keyed by the trait's uuid."""

    __row__: ClassVar[type[Row]] = TraitDecor

    @Database.commit_after_this
    def create(self, uuid: UUID, color: str) -> TraitDecor:
        row = TraitDecor(uuid=uuid, color=color)
        Database.add(row)
        Database.flush()
        return row


trait_decor = TraitDecors()
