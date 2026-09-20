"""The traits table as a Mapping of writable traits (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.objects.tables.table_traits import TABLE_Traits as TABLE_Traits
from nylium.objects.tables.table_type_traits import TABLE_TypeTraits as TABLE_TypeTraits
from nylium.objects.rows.trait import Trait as Trait
from nylium.objects.rows.type_trait import TypeTrait as TypeTrait
from nylium.objects.tables.type_traits import TypeTraits as TypeTraits, type_traits

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

    @Database.commit_after_this
    def create(self, name: str, color: str) -> Trait:
        from nylium.tables.decor import trait_decor

        row = TABLE_Traits(name=name)
        Database.add(row)
        Database.flush()
        _ = trait_decor.create(row.uuid, color)
        return Trait(row)

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(TABLE_Traits, uuid)
        if row is not None:
            Database.delete(row)  # its props cascade


@Database.use_same_session
def uuid_by_name(name: str) -> UUID | None:
    """The trait uuid for a name, or None (ADR-0019: trait lookup)."""
    return Database.scalar(
        sqla.select(TABLE_Traits.uuid).where(TABLE_Traits.name == name)
    )


@Database.use_same_session
def name_of(uuid: UUID) -> str | None:
    """The trait's name by uuid, or None when the trait is gone (ADR-0019)."""
    row = Database.get(TABLE_Traits, uuid)
    return None if row is None else str(row.name)


traits = Traits()
