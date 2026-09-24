"""Traits table store for Trait."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.Row import mapper
from nylium.database.Table import Row, Table
from nylium.data.rows import Trait
from nylium.data.tables.decor import trait_decor

class Traits(Table[UUID, Trait]):
    """The traits table as a Mapping of writable traits."""

    __row__: ClassVar[type[Row]] = Trait

    @Database.commit_after_this
    def create(self, name: str, color: str) -> Trait:

        row = Trait(name=name)
        Database.add(row)
        Database.flush()
        _ = trait_decor.create(row.uuid, color)
        return row

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(Trait, uuid)
        if row is not None:
            Database.delete(row)  # its props cascade

    @classmethod
    @Database.use_same_session
    def uuid_by_name(cls, name: str) -> UUID | None:
        """The trait uuid for a name, or None (ADR-0019: trait lookup)."""
        c = mapper(Trait).columns
        return Database.scalar(sqla.select(c.uuid).where(c.name == name))

    @classmethod
    @Database.use_same_session
    def name_of(cls, uuid: UUID) -> str | None:
        """The trait's name by uuid, or None when the trait is gone."""
        row = Database.get(Trait, uuid)
        return None if row is None else str(row.name)

traits = Traits()
