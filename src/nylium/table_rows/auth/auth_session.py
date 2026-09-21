"""The auth_sessions table: AuthSession (mapped Row) + AuthSessions (store)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class AuthSession(Row):
    __tablename__: ClassVar[str] = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSessions(Table[str, AuthSession]):
    """The auth_sessions table as a Mapping keyed by token hash."""

    __row__: ClassVar[type[Row]] = AuthSession

    @Database.commit_after_this
    def create(self, user_uuid: UUID, token_hash: str, expires_at: datetime) -> None:
        Database.add(
            AuthSession(token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at)
        )

    @Database.commit_after_this
    def delete(self, token_hash: str) -> None:
        row = Database.get(AuthSession, token_hash)
        if row is not None:
            Database.delete(row)

    @Database.commit_after_this
    def purge_expired(self) -> None:
        c = mapper(AuthSession).columns
        _ = Database.execute(
            sqla.delete(AuthSession).where(c.expires_at <= datetime.now(timezone.utc))
        )


auth_sessions = AuthSessions()
