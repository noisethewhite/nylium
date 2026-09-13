from __future__ import annotations

# Passkey (WebAuthn) infrastructure. System tables like TABLE_Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.
from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_AuthUsers:
    __tablename__: ClassVar[str] = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, nullable=False
    )
