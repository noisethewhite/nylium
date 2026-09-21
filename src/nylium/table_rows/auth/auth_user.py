"""The auth_users table: AuthUser (mapped Row) + AuthUsers (store)."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class AuthUser(Row):
    __tablename__: ClassVar[str] = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, nullable=False
    )


class AuthUsers(Table[UUID, AuthUser]):
    """The auth_users table as a Mapping of writable users."""

    __row__: ClassVar[type[Row]] = AuthUser

    @Database.commit_after_this
    def create(self, name: str) -> AuthUser:
        row = AuthUser(name=name)
        Database.add(row)
        Database.flush()
        return row


auth_users = AuthUsers()
