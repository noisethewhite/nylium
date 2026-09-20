"""The trait_decor table as a Mapping keyed by the trait's uuid."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, commit_after_this
from nylium.database.table import Row, Table
from nylium.tables.decor.table_trait_decor import TABLE_TraitDecor
from nylium.tables.decor.trait_decor import TraitDecor


class TraitDecors(Table[UUID, TraitDecor]):
    """The trait_decor table as a Mapping keyed by the trait's uuid."""

    __row__: ClassVar[type[Row]] = TraitDecor

    @commit_after_this
    def create(self, uuid: UUID, color: str) -> TraitDecor:
        row = TABLE_TraitDecor(uuid=uuid, color=color)
        Database.add(row)
        Database.flush()
        return TraitDecor(row)


trait_decor = TraitDecors()
