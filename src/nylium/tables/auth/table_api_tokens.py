from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_ApiTokens:
    """API access tokens (ADR-0009 §3): the client holds a raw bearer
    token, the table stores only its sha256. Scoped ('read' | 'read-write')
    and revocable — the seam for Grimaud's automation, never a back door."""

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
