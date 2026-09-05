from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


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
    @Database.sessionmethod(bundled=False, commit=True)
    def create(
        cls,
        session: Session,
        uuid: UUID,
        type_name: str,
        name: str,
        mime: str,
        size_bytes: int,
    ) -> None:
        session.add(
            Files(uuid=uuid, type_name=type_name, name=name, mime=mime, size_bytes=size_bytes)
        )
        session.flush()

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_uuid(cls, session: Session, uuid: UUID) -> "Files | None":
        return session.get(cls, uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_uuids(cls, session: Session) -> list[UUID]:
        return list(session.scalars(sqla.select(cls.uuid)).all())

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def list_all(cls, session: Session) -> list["Files"]:
        return list(session.scalars(sqla.select(cls).order_by(cls.name)).all())

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def rename(cls, session: Session, uuid: UUID, name: str) -> None:
        row = session.get(cls, uuid)
        if row is None:
            raise KeyError(f"no file {uuid}")
        row.name = name

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def delete_by_uuid(cls, session: Session, uuid: UUID) -> None:
        row = session.get(cls, uuid)
        if row is not None:
            session.delete(row)
