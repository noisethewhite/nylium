# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
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


class ApiToken(Row):
    """One API token: a writable snapshot of an api_tokens row."""

    __table__: ClassVar[type[Base]] = TABLE_ApiTokens

    uuid: UUID
    user_uuid: UUID
    name: str
    token_hash: str
    scope: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiTokens(Table[UUID, ApiToken]):
    """The api_tokens table as a Mapping of writable tokens."""

    __row__: ClassVar[type[Row]] = ApiToken

    @databasemethod(commit=True)
    def create(self, user_uuid: UUID, name: str, token_hash: str, scope: str) -> ApiToken:
        row = TABLE_ApiTokens(
            user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope
        )
        Database.session.add(row)
        Database.session.flush()  # populate uuid/created_at before the session ends
        return ApiToken(row)


api_tokens = ApiTokens()
