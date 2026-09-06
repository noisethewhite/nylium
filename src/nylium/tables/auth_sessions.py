from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


class AuthSessions(Base):
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

    @classmethod
    @databasemethod(commit=True)
    def create(
        cls, user_uuid: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        Database.session.add(
            cls(token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at)
        )

    @classmethod
    @databasemethod(commit=False)
    def by_hash(cls, token_hash: str) -> "AuthSessions | None":
        return Database.session.get(cls, token_hash)

    @classmethod
    @databasemethod(commit=True)
    def refresh(cls, token_hash: str, expires_at: datetime) -> None:
        row = Database.session.get(cls, token_hash)
        if row is not None:
            row.expires_at = expires_at

    @classmethod
    @databasemethod(commit=True)
    def delete(cls, token_hash: str) -> None:
        row = Database.session.get(cls, token_hash)
        if row is not None:
            Database.session.delete(row)

    @classmethod
    @databasemethod(commit=True)
    def purge_expired(cls,) -> None:
        _ = Database.session.execute(
            sqla.delete(cls).where(cls.expires_at <= datetime.now(timezone.utc))
        )
