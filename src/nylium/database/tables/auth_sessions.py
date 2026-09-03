from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


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
    @Database.sessionmethod(bundled=False, commit=True)
    def create(
        cls, session: Session, user_uuid: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        session.add(
            cls(token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at)
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_hash(cls, session: Session, token_hash: str) -> "AuthSessions | None":
        return session.get(cls, token_hash)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def refresh(cls, session: Session, token_hash: str, expires_at: datetime) -> None:
        row = session.get(cls, token_hash)
        if row is not None:
            row.expires_at = expires_at

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def delete(cls, session: Session, token_hash: str) -> None:
        row = session.get(cls, token_hash)
        if row is not None:
            session.delete(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def purge_expired(cls, session: Session) -> None:
        _ = session.execute(
            sqla.delete(cls).where(cls.expires_at <= datetime.now(timezone.utc))
        )
