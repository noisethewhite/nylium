from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_AuthSessions:
    """Server-side sessions: the cookie carries a random token, the table
    stores only its sha256 — a leaked dump yields no usable tokens."""
    __tablename__: ClassVar[str] = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
