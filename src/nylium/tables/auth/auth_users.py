from __future__ import annotations

# Passkey (WebAuthn) infrastructure. System tables like TABLE_Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.
from datetime import datetime
from typing import ClassVar, cast
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base


class TABLE_AuthUsers(Base):
    __tablename__: str = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthUser(TableDomain):
    """One auth user: a writable snapshot of a TABLE_AuthUsers row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthUsers

    uuid: tableproperty[AuthUser, UUID] = tableproperty()
    name: tableproperty[AuthUser, str] = tableproperty()
    created_at: tableproperty[AuthUser, datetime] = tableproperty()


class AuthUsers(TableMapping[UUID, AuthUser]):
    """The auth_users table as a Mapping of writable users."""

    __domain__: ClassVar[type[TableDomain]] = AuthUser

    @databasemethod(commit=True)
    def create(self, name: str) -> AuthUser:
        """Insert a user, returning its domain object (uuid/created_at
        populated by the flush)."""
        row = TABLE_AuthUsers(name=name)
        Database.session.add(row)
        Database.session.flush()  # populate uuid/created_at before the session ends
        return cast(AuthUser, AuthUser.from_row(row))


auth_users = AuthUsers()
