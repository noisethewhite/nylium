"""Types table store for Type."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.data.rows.objects.type import Type
from nylium.data.tables.decor.type_decors import type_decor

class Types(Table[UUID, Type]):
    """The types table as a Mapping of writable types."""

    __row__: ClassVar[type[Row]] = Type

    @Database.commit_after_this
    def create(
        self,
        name: str,
        plural_name: str,
        icon: str | None = None,
        kind: str | None = None,
        embedded: bool | None = None,
    ) -> Type:

        row = Type(name=name)
        if kind is not None:
            row.kind = kind
        if embedded is not None:
            row.embedded = embedded
        Database.add(row)
        Database.flush()
        _ = type_decor.create(row.uuid, plural_name, icon, None)
        return row

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(Type, uuid)
        if row is not None:
            Database.delete(row)  # its props cascade

types = Types()
