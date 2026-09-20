# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, commit_after_this, use_same_session
from nylium.database.table import Row, Table
from nylium.tables.file import File as File
from nylium.tables.table_files import TABLE_Files as TABLE_Files


class Files(Table[UUID, File]):
    """The files table as a Mapping of writable files."""

    __row__: ClassVar[type[Row]] = File

    @commit_after_this
    def create(
        self,
        uuid: UUID,
        type_name: str,
        name: str,
        mime: str,
        size_bytes: int,
    ) -> File:
        row = TABLE_Files(
            uuid=uuid,
            type_name=type_name,
            name=name,
            mime=mime,
            size_bytes=size_bytes,
        )
        Database.add(row)
        Database.flush()
        return File(row)

    @commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(TABLE_Files, uuid)
        if row is not None:
            Database.delete(row)


@use_same_session
def type_name_of(uuid: UUID) -> str | None:
    """The stored type_name for a file uuid, or None (ADR-0019)."""
    row = Database.get(TABLE_Files, uuid)
    return None if row is None else row.type_name


files = Files()
