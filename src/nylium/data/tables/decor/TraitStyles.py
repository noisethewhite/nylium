"""TraitStyles table store for TraitStyle."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.Table import Row, Table
from nylium.data.rows import TraitStyle

class TraitStyles(Table[UUID, TraitStyle]):
    """The trait_style table as a Mapping keyed by the trait's uuid."""

    __row__: ClassVar[type[Row]] = TraitStyle

    @Database.commit_after_this
    def create(self, uuid: UUID, color: str) -> TraitStyle:
        row = TraitStyle(uuid=uuid, color=color)
        Database.add(row)
        Database.flush()
        return row

trait_style = TraitStyles()
