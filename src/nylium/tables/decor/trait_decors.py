"""TraitDecors table store for TraitDecor."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.decor.trait_decor import TraitDecor

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
