from collections.abc import Generator
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
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


class File(TableDomain):
    """One file: a writable snapshot of a TABLE_Files row."""

    __table__: ClassVar[type[Base]] = TABLE_Files

    uuid: tableproperty[UUID] = tableproperty()
    type_name: tableproperty[str] = tableproperty()
    name: tableproperty[str] = tableproperty()
    mime: tableproperty[str] = tableproperty()
    size_bytes: tableproperty[int] = tableproperty()

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape (ADR-0011 §5), matching the file
        contract the old FileView serialized."""
        return {
            "uuid": str(self.uuid),
            "type_name": self.type_name,
            "name": self.name,
            "mime": self.mime,
            "size_bytes": self.size_bytes,
        }


class Files(TableMapping[UUID, File]):
    """The files table as a Mapping of writable files."""

    __domain__: ClassVar[type[TableDomain]] = File

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
        return cast(File, File.from_row(row))

    def list_all(self) -> Generator[File, None, None]:
        """Every file, name-ordered, lazily."""
        with SessionContext():
            all_files = [
                cast(File, File.from_row(row))
                for row in Database.session.scalars(
                    sqla.select(TABLE_Files).order_by(TABLE_Files.name)
                )
            ]
        yield from all_files

    @databasemethod(commit=True)
    def rename(self, uuid: UUID, name: str) -> None:
        row = Database.session.get(TABLE_Files, uuid)
        if row is None:
            raise KeyError(f"no file {uuid}")
        row.name = name

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Files, uuid)
        if row is not None:
            Database.session.delete(row)


files = Files()
