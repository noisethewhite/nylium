"""Instance mapped row."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class Instance(Row):
    __tablename__: ClassVar[str] = "instances"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(ForeignKey("types.uuid"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    owner_object_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    owner_prop_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, onupdate=func.now()
    )
