"""The auth_challenges table: AuthChallenge (mapped Row) + AuthChallenges (store)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class AuthChallenge(Row):
    __tablename__: ClassVar[str] = "auth_challenges"

    challenge: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    user_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"),
        nullable=True,
        default=None,
        kw_only=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthChallenges(Table[bytes, AuthChallenge]):
    """The auth_challenges table as a Mapping keyed by challenge bytes."""

    __row__: ClassVar[type[Row]] = AuthChallenge

    REGISTER_KIND: ClassVar[str] = "register"
    LOGIN_KIND: ClassVar[str] = "login"

    @Database.commit_after_this
    def issue(
        self, challenge: bytes, kind: str, user_uuid: UUID | None, ttl_seconds: int
    ) -> None:
        self.purge_expired()
        Database.add(
            AuthChallenge(
                challenge=challenge,
                kind=kind,
                user_uuid=user_uuid,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            )
        )

    @Database.commit_after_this
    def consume(self, challenge: bytes, kind: str) -> tuple[bool, UUID | None]:
        c = mapper(AuthChallenge).columns
        row = Database.get(AuthChallenge, challenge)
        if row is None:
            return False, None
        user_uuid = row.user_uuid
        alive = row.expires_at > datetime.now(timezone.utc)
        _ = Database.execute(
            sqla.delete(AuthChallenge).where(c.challenge == challenge)
        )
        if row.kind != kind or not alive:
            return False, None
        return True, user_uuid

    @Database.commit_after_this
    def purge_expired(self) -> None:
        c = mapper(AuthChallenge).columns
        _ = Database.execute(
            sqla.delete(AuthChallenge).where(
                c.expires_at <= datetime.now(timezone.utc)
            )
        )


auth_challenges = AuthChallenges()
