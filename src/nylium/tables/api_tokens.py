from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


class TABLE_ApiTokens(Base):
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
    @databasemethod(commit=True)
    def create(
        cls, user_uuid: UUID, name: str, token_hash: str, scope: str
    ) -> "TABLE_ApiTokens":
        row = cls(user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope)
        Database.session.add(row)
        Database.session.flush()  # populate uuid/created_at before the session ends
        return row

    @classmethod
    @databasemethod(commit=False)
    def by_hash(cls, token_hash: str) -> "TABLE_ApiTokens | None":
        return Database.session.scalar(sqla.select(cls).where(cls.token_hash == token_hash))

    @classmethod
    @databasemethod(commit=False)
    def for_user(cls, user_uuid: UUID) -> list["TABLE_ApiTokens"]:
        return list(
            Database.session.scalars(
                sqla.select(cls).where(cls.user_uuid == user_uuid).order_by(cls.created_at)
            ).all()
        )

    @classmethod
    @databasemethod(commit=True)
    def mark_used(cls, uuid: UUID) -> None:
        row = Database.session.get(cls, uuid)
        if row is not None:
            row.last_used_at = datetime.now(timezone.utc)

    @classmethod
    @databasemethod(commit=True)
    def revoke(cls, user_uuid: UUID, uuid: UUID) -> bool:
        row = Database.session.get(cls, uuid)
        if row is None or row.user_uuid != user_uuid:
            return False
        row.revoked_at = datetime.now(timezone.utc)
        return True
