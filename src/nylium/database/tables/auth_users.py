# Passkey (WebAuthn) infrastructure. System tables like Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


class AuthUsers(Base):
    __tablename__: str = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def create(cls, session: Session, name: str) -> "AuthUsers":
        user = cls(name=name)
        session.add(user)
        session.flush()  # populate uuid/created_at before the session ends
        return user

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_uuid(cls, session: Session, uuid: UUID) -> "AuthUsers | None":
        return session.get(cls, uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_name(cls, session: Session, name: str) -> "AuthUsers | None":
        return session.scalar(sqla.select(cls).where(cls.name == name))
