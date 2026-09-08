# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import Base


# Self-contained file entity (ADR-0008): no FK to instances — the uuid IS
# the pointer, stable for the life of the file. The blob lives on disk at
# FILES_DIR/<uuid>. `name` is a freely renameable display name (defaults to
# the original filename on upload); `type_name` is File/Document/Image.
class TABLE_Files(Base):
    __tablename__: str = "files"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_name: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)


class File(Row):
    """One file: a writable snapshot of a TABLE_Files row."""

    __table__: ClassVar[type[Base]] = TABLE_Files

    uuid: UUID
    type_name: str
    name: str
    mime: str
    size_bytes: int

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape, matching web/src/contracts.ts FileView."""
        return {
            "uuid": str(self.uuid),
            "type_name": self.type_name,
            "name": self.name,
            "mime": self.mime,
            "size_bytes": self.size_bytes,
        }


class Files(Table[UUID, File]):
    """The files table as a Mapping of writable files."""

    __row__: ClassVar[type[Row]] = File

    @databasemethod(commit=True)
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
        Database.session.add(row)
        Database.session.flush()
        return File(row)

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Files, uuid)
        if row is not None:
            Database.session.delete(row)


files = Files()
