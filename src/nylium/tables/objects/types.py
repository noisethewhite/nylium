"""The types table as a Mapping of writable types (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.objects.table_types import TABLE_Types as TABLE_Types
from nylium.rows.objects.type import Type as Type

__all__ = ["TABLE_Types", "Type", "Types", "types"]

# TABLE_Types lives in table_types.py (see that module's docstring) and is
# re-exported here: `from nylium.tables.objects.types import TABLE_Types` keeps
# working everywhere. `Type` is re-exported from type.py.


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
        from nylium.tables.decor import type_decor

        row = TABLE_Types(name=name)
        if kind is not None:
            row.kind = kind
        if embedded is not None:
            row.embedded = embedded
        Database.add(row)
        Database.flush()
        # ADR-0014: decor column defaults apply where the caller passes none
        _ = type_decor.create(row.uuid, plural_name, icon, None)
        return Type(row)

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(TABLE_Types, uuid)
        if row is not None:
            Database.delete(row)  # its props cascade


types = Types()
