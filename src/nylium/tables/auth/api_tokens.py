from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
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


class ApiToken(TableDomain):
    """One API token: a writable snapshot of an api_tokens row."""

    __table__: ClassVar[type[Base]] = TABLE_ApiTokens

    uuid: tableproperty[ApiToken, UUID] = tableproperty()
    user_uuid: tableproperty[ApiToken, UUID] = tableproperty()
    name: tableproperty[ApiToken, str] = tableproperty()
    token_hash: tableproperty[ApiToken, str] = tableproperty()
    scope: tableproperty[ApiToken, str] = tableproperty()
    created_at: tableproperty[ApiToken, datetime] = tableproperty()
    last_used_at: tableproperty[ApiToken, datetime | None] = tableproperty()
    revoked_at: tableproperty[ApiToken, datetime | None] = tableproperty()


class ApiTokens(TableMapping[UUID, ApiToken]):
    """The api_tokens table as a Mapping of writable tokens."""

    __domain__: ClassVar[type[TableDomain]] = ApiToken

    @databasemethod(commit=True)
    def create(self, user_uuid: UUID, name: str, token_hash: str, scope: str) -> ApiToken:
        row = TABLE_ApiTokens(
            user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope
        )
        Database.session.add(row)
        Database.session.flush()  # populate uuid/created_at before the session ends
        return cast(ApiToken, ApiToken.from_row(row))

    @databasemethod(commit=False)
    def by_hash(self, token_hash: str) -> ApiToken | None:
        row = Database.session.scalar(
            sqla.select(TABLE_ApiTokens).where(
                TABLE_ApiTokens.token_hash == token_hash
            )
        )
        return None if row is None else cast(ApiToken, ApiToken.from_row(row))

    @databasemethod(commit=False)
    def for_user(self, user_uuid: UUID) -> list[ApiToken]:
        rows = list(
            Database.session.scalars(
                sqla.select(TABLE_ApiTokens)
                .where(TABLE_ApiTokens.user_uuid == user_uuid)
                .order_by(TABLE_ApiTokens.created_at)
            ).all()
        )
        return [cast(ApiToken, ApiToken.from_row(row)) for row in rows]

    @databasemethod(commit=True)
    def mark_used(self, uuid: UUID) -> None:
        token = self.get(uuid)
        if token is not None:
            token.last_used_at = datetime.now(timezone.utc)

    @databasemethod(commit=True)
    def revoke(self, user_uuid: UUID, uuid: UUID) -> bool:
        token = self.get(uuid)
        if token is None or token.user_uuid != user_uuid:
            return False
        token.revoked_at = datetime.now(timezone.utc)
        return True


api_tokens = ApiTokens()
