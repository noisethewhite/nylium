"""Files table store for File."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.data.rows.file import File

class Files(Table[UUID, File]):
    """The files table as a Mapping of writable files."""

    __row__: ClassVar[type[Row]] = File

    @Database.commit_after_this
    def create(
        self,
        uuid: UUID,
        type_name: str,
        name: str,
        mime: str,
        size_bytes: int,
    ) -> File:
        row = File(
            uuid=uuid,
            type_name=type_name,
            name=name,
            mime=mime,
            size_bytes=size_bytes,
        )
        Database.add(row)
        Database.flush()
        return row

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(File, uuid)
        if row is not None:
            Database.delete(row)

    @classmethod
    @Database.use_same_session
    def type_name_of(cls, uuid: UUID) -> str | None:
        """The stored type_name for a file uuid, or None (ADR-0019)."""
        row = Database.get(File, uuid)
        return None if row is None else row.type_name

files = Files()
