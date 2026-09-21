"""The api_tokens table: ApiToken (mapped Row) + ApiTokens (store)."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class ApiToken(Row):
    __tablename__: ClassVar[str] = "api_tokens"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class ApiTokens(Table[UUID, ApiToken]):
    """The api_tokens table as a Mapping of writable tokens."""

    __row__: ClassVar[type[Row]] = ApiToken

    @Database.commit_after_this
    def create(
        self, user_uuid: UUID, name: str, token_hash: str, scope: str
    ) -> ApiToken:
        row = ApiToken(user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope)
        Database.add(row)
        Database.flush()
        return row


api_tokens = ApiTokens()
