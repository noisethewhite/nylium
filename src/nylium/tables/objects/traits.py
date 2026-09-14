"""The traits table as a Mapping of writable traits (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.objects.table_traits import TABLE_Traits as TABLE_Traits
from nylium.tables.objects.table_type_traits import TABLE_TypeTraits as TABLE_TypeTraits
from nylium.tables.objects.trait import Trait as Trait
from nylium.tables.objects.type_trait import TypeTrait as TypeTrait
from nylium.tables.objects.type_traits import TypeTraits as TypeTraits, type_traits

__all__ = [
    "TABLE_Traits",
    "TABLE_TypeTraits",
    "Trait",
    "Traits",
    "TypeTrait",
    "TypeTraits",
    "traits",
    "type_traits",
]


class Traits(Table[UUID, Trait]):
    """The traits table as a Mapping of writable traits."""

    __row__: ClassVar[type[Row]] = Trait

    @databasemethod(commit=True)
    def create(self, name: str, color: str) -> Trait:
        from nylium.tables.decor import trait_decor

        row = TABLE_Traits(name=name)
        Database.session.add(row)
        Database.session.flush()
        _ = trait_decor.create(row.uuid, color)
        return Trait(row)

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Traits, uuid)
        if row is not None:
            Database.session.delete(row)  # its props cascade


@databasemethod(commit=False)
def uuid_by_name(name: str) -> UUID | None:
    """The trait uuid for a name, or None (ADR-0019: trait lookup)."""
    return Database.session.scalar(
        sqla.select(TABLE_Traits.uuid).where(TABLE_Traits.name == name)
    )


traits = Traits()
