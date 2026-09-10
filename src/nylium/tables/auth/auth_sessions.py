# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import reg

@reg.mapped_as_dataclass
class TABLE_AuthSessions:
    """Server-side sessions: the cookie carries a random token, the table
    stores only its sha256 — a leaked dump yields no usable tokens."""
    __tablename__: ClassVar[str] = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuthSession(Row):
    """One server-side session: a writable snapshot of an auth_sessions row."""

    __table__: ClassVar[type[object]] = TABLE_AuthSessions

    token_hash: str
    user_uuid: UUID
    expires_at: datetime


class AuthSessions(Table[str, AuthSession]):
    """The auth_sessions table as a Mapping keyed by token hash."""

    __row__: ClassVar[type[Row]] = AuthSession

    @databasemethod(commit=True)
    def create(self, user_uuid: UUID, token_hash: str, expires_at: datetime) -> None:
        Database.session.add(
            TABLE_AuthSessions(
                token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at
            )
        )

    @databasemethod(commit=True)
    def delete(self, token_hash: str) -> None:
        row = Database.session.get(TABLE_AuthSessions, token_hash)
        if row is not None:
            Database.session.delete(row)

    @databasemethod(commit=True)
    def purge_expired(self) -> None:
        _ = Database.session.execute(
            sqla.delete(TABLE_AuthSessions).where(
                TABLE_AuthSessions.expires_at <= datetime.now(timezone.utc)
            )
        )


auth_sessions = AuthSessions()
