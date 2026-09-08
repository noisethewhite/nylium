# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

# Passkey (WebAuthn) infrastructure. System tables like TABLE_Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.
from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import Base


class TABLE_AuthUsers(Base):
    __tablename__: str = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthUser(Row):
    """One auth user: a writable snapshot of a TABLE_AuthUsers row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthUsers

    uuid: UUID
    name: str
    created_at: datetime


class AuthUsers(Table[UUID, AuthUser]):
    """The auth_users table as a Mapping of writable users."""

    __row__: ClassVar[type[Row]] = AuthUser

    @databasemethod(commit=True)
    def create(self, name: str) -> AuthUser:
        """Insert a user, returning its row (uuid/created_at populated by
        the flush)."""
        row = TABLE_AuthUsers(name=name)
        Database.session.add(row)
        Database.session.flush()
        return AuthUser(row)


auth_users = AuthUsers()
