# Passkey (WebAuthn) infrastructure. System tables like TABLE_Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


class TABLE_AuthUsers(Base):
    __tablename__: str = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    @databasemethod(commit=True)
    def create(cls, name: str) -> "TABLE_AuthUsers":
        user = cls(name=name)
        Database.session.add(user)
        Database.session.flush()  # populate uuid/created_at before the session ends
        return user

    @classmethod
    @databasemethod(commit=False)
    def by_uuid(cls, uuid: UUID) -> "TABLE_AuthUsers | None":
        return Database.session.get(cls, uuid)

    @classmethod
    @databasemethod(commit=False)
    def by_name(cls, name: str) -> "TABLE_AuthUsers | None":
        return Database.session.scalar(sqla.select(cls).where(cls.name == name))
