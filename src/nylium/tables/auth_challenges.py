from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


class TABLE_AuthChallenges(Base):
    """One-shot WebAuthn challenges. Consumed on use, dead after TTL."""
    __tablename__: str = "auth_challenges"

    REGISTER_KIND: ClassVar[str] = "register"
    LOGIN_KIND: ClassVar[str] = "login"

    challenge: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    user_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @classmethod
    @databasemethod(commit=True)
    def issue(
        cls,
        challenge: bytes,
        kind: str,
        user_uuid: UUID | None,
        ttl_seconds: int,
    ) -> None:
        cls.purge_expired()
        Database.session.add(
            cls(
                challenge=challenge,
                kind=kind,
                user_uuid=user_uuid,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=ttl_seconds),
            )
        )

    @classmethod
    @databasemethod(commit=True)
    def consume(
        cls, challenge: bytes, kind: str
    ) -> tuple[bool, UUID | None]:
        """Pop a challenge row: valid only if it exists, matches the
        ceremony kind and has not expired. One use, then gone.
        Returns (valid, user_uuid bound at issue time — None for login)."""
        row = Database.session.get(cls, challenge)
        if row is None:
            return False, None
        user_uuid = row.user_uuid
        alive = row.expires_at > datetime.now(timezone.utc)
        _ = Database.session.execute(sqla.delete(cls).where(cls.challenge == challenge))
        if row.kind != kind or not alive:
            return False, None
        return True, user_uuid

    @classmethod
    @databasemethod(commit=True)
    def purge_expired(cls,) -> None:
        _ = Database.session.execute(
            sqla.delete(cls).where(cls.expires_at <= datetime.now(timezone.utc))
        )
