# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import reg

@reg.mapped_as_dataclass
class TABLE_AuthChallenges:
    """One-shot WebAuthn challenges. Consumed on use, dead after TTL."""
    __tablename__: ClassVar[str] = "auth_challenges"

    challenge: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    user_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=True, default=None, kw_only=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuthChallenge(Row):
    """One WebAuthn challenge: a writable snapshot of an auth_challenges row."""

    __table__: ClassVar[type[object]] = TABLE_AuthChallenges

    challenge: bytes
    kind: str
    user_uuid: UUID | None
    expires_at: datetime


class AuthChallenges(Table[bytes, AuthChallenge]):
    """The auth_challenges table as a Mapping keyed by challenge bytes.

    Challenges are one-shot ceremony state: issued, consumed once, purged
    on TTL. The Mapping shape is for consistency with the other tables;
    iteration is never meaningful here."""

    __row__: ClassVar[type[Row]] = AuthChallenge

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
