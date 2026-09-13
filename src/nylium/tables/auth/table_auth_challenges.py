from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

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
