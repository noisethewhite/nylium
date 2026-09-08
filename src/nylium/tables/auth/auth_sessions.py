from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base


class TABLE_AuthSessions(Base):
    """Server-side sessions: the cookie carries a random token, the table
    stores only its sha256 — a leaked dump yields no usable tokens."""
    __tablename__: str = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuthSession(TableDomain):
    """One server-side session: a writable snapshot of an auth_sessions row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthSessions

    token_hash: tableproperty[AuthSession, str] = tableproperty()
    user_uuid: tableproperty[AuthSession, UUID] = tableproperty()
    expires_at: tableproperty[AuthSession, datetime] = tableproperty()


class AuthSessions(TableMapping[str, AuthSession]):
    """The auth_sessions table as a Mapping keyed by token hash."""

    __domain__: ClassVar[type[TableDomain]] = AuthSession

    @databasemethod(commit=True)
    def create(self, user_uuid: UUID, token_hash: str, expires_at: datetime) -> None:
        Database.session.add(
            TABLE_AuthSessions(
                token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at
            )
        )

    @databasemethod(commit=True)
    def refresh(self, token_hash: str, expires_at: datetime) -> None:
        session = self.get(token_hash)
        if session is not None:
            session.expires_at = expires_at

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
