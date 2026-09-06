from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


# Self-contained file entity (ADR-0008): no FK to instances — the uuid IS
# the pointer, stable for the life of the file. The blob lives on disk at
# FILES_DIR/<uuid>. `name` is a freely renameable display name (defaults to
# the original filename on upload); `type_name` is File/Document/Image.
class Files(Base):
    __tablename__: str = "files"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_name: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)

    @classmethod
    @databasemethod(commit=True)
    def create(
        cls,
        uuid: UUID,
        type_name: str,
        name: str,
        mime: str,
        size_bytes: int,
    ) -> None:
        Database.session.add(
            Files(uuid=uuid, type_name=type_name, name=name, mime=mime, size_bytes=size_bytes)
        )
        Database.session.flush()

    @classmethod
    @databasemethod(commit=False)
    def by_uuid(cls, uuid: UUID) -> "Files | None":
        return Database.session.get(cls, uuid)

    @classmethod
    @databasemethod(commit=False)
    def all_uuids(cls,) -> list[UUID]:
        return list(Database.session.scalars(sqla.select(cls.uuid)).all())

    @classmethod
    @databasemethod(commit=False)
    def list_all(cls,) -> list["Files"]:
        return list(Database.session.scalars(sqla.select(cls).order_by(cls.name)).all())

    @classmethod
    @databasemethod(commit=True)
    def rename(cls, uuid: UUID, name: str) -> None:
        row = Database.session.get(cls, uuid)
        if row is None:
            raise KeyError(f"no file {uuid}")
        row.name = name

    @classmethod
    @databasemethod(commit=True)
    def delete_by_uuid(cls, uuid: UUID) -> None:
        row = Database.session.get(cls, uuid)
        if row is not None:
            Database.session.delete(row)
