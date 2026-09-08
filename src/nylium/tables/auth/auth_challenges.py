from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base


class TABLE_AuthChallenges(Base):
    """One-shot WebAuthn challenges. Consumed on use, dead after TTL."""
    __tablename__: str = "auth_challenges"

    challenge: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    user_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuthChallenge(TableDomain):
    """One WebAuthn challenge: a writable snapshot of an auth_challenges row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthChallenges

    challenge: tableproperty[AuthChallenge, bytes] = tableproperty()
    kind: tableproperty[AuthChallenge, str] = tableproperty()
    user_uuid: tableproperty[AuthChallenge, UUID | None] = tableproperty()
    expires_at: tableproperty[AuthChallenge, datetime] = tableproperty()


class AuthChallenges(TableMapping[bytes, AuthChallenge]):
    """The auth_challenges table as a Mapping keyed by challenge bytes.

    Challenges are one-shot ceremony state: issued, consumed once, purged
    on TTL. The Mapping shape is for consistency with the other tables;
    iteration is never meaningful here."""

    __domain__: ClassVar[type[TableDomain]] = AuthChallenge

    REGISTER_KIND: ClassVar[str] = "register"
    LOGIN_KIND: ClassVar[str] = "login"

    @databasemethod(commit=True)
    def issue(
        self, challenge: bytes, kind: str, user_uuid: UUID | None, ttl_seconds: int
    ) -> None:
        self.purge_expired()
        Database.session.add(
            TABLE_AuthChallenges(
                challenge=challenge,
                kind=kind,
                user_uuid=user_uuid,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=ttl_seconds),
            )
        )

    @databasemethod(commit=True)
    def consume(self, challenge: bytes, kind: str) -> tuple[bool, UUID | None]:
        """Pop a challenge row: valid only if it exists, matches the
        ceremony kind and has not expired. One use, then gone.
        Returns (valid, user_uuid bound at issue time — None for login)."""
        row = Database.session.get(TABLE_AuthChallenges, challenge)
        if row is None:
            return False, None
        user_uuid = row.user_uuid
        alive = row.expires_at > datetime.now(timezone.utc)
        _ = Database.session.execute(
            sqla.delete(TABLE_AuthChallenges).where(
                TABLE_AuthChallenges.challenge == challenge
            )
        )
        if row.kind != kind or not alive:
            return False, None
        return True, user_uuid

    @databasemethod(commit=True)
    def purge_expired(self) -> None:
        _ = Database.session.execute(
            sqla.delete(TABLE_AuthChallenges).where(
                TABLE_AuthChallenges.expires_at <= datetime.now(timezone.utc)
            )
        )


auth_challenges = AuthChallenges()
