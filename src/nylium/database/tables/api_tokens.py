from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


class ApiTokens(Base):
    """API access tokens (ADR-0009 §3): the client holds a raw bearer
    token, the table stores only its sha256. Scoped ('read' | 'read-write')
    and revocable — the seam for Grimaud's automation, never a back door."""

    __tablename__: str = "api_tokens"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def create(
        cls, session: Session, user_uuid: UUID, name: str, token_hash: str, scope: str
    ) -> "ApiTokens":
        row = cls(user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope)
        session.add(row)
        session.flush()  # populate uuid/created_at before the session ends
        return row

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_hash(cls, session: Session, token_hash: str) -> "ApiTokens | None":
        return session.scalar(sqla.select(cls).where(cls.token_hash == token_hash))

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def for_user(cls, session: Session, user_uuid: UUID) -> list["ApiTokens"]:
        return list(
            session.scalars(
                sqla.select(cls).where(cls.user_uuid == user_uuid).order_by(cls.created_at)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def mark_used(cls, session: Session, uuid: UUID) -> None:
        row = session.get(cls, uuid)
        if row is not None:
            row.last_used_at = datetime.now(timezone.utc)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def revoke(cls, session: Session, user_uuid: UUID, uuid: UUID) -> bool:
        row = session.get(cls, uuid)
        if row is None or row.user_uuid != user_uuid:
            return False
        row.revoked_at = datetime.now(timezone.utc)
        return True
