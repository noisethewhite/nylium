from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


# Blob metadata for File/Document/Image instances (ADR-0006): the bytes
# live on disk at FILES_DIR/<instance uuid>, this row carries only what
# the bytes can't say about themselves. The row exists exactly while the
# instance exists.
class Files(Base):
    __tablename__: str = "files"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def create(
        cls, session: Session, uuid: UUID, mime: str, size_bytes: int
    ) -> None:
        session.add(Files(uuid=uuid, mime=mime, size_bytes=size_bytes))
        session.flush()

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_uuid(cls, session: Session, uuid: UUID) -> "Files | None":
        return session.get(cls, uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_uuids(cls, session: Session) -> list[UUID]:
        return list(session.scalars(sqla.select(cls.uuid)).all())
