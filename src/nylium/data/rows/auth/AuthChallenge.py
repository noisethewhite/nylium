"""AuthChallenge mapped row."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

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
