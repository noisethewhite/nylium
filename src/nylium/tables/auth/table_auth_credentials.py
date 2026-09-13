from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_AuthCredentials:
    __tablename__: ClassVar[str] = "auth_credentials"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transports: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
