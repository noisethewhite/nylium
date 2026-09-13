"""Instances of types — arrays and scalars are types too (raw row mapping)."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_Instances:
    """Instances of types — arrays and scalars are types too."""

    __tablename__: ClassVar[str] = "instances"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Every instance carries both forms (ADR-0011 phase 8), same rule as
    # types.plural_name; Instances.create derives "<name>s" by default
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Ownership read-index for embedded instances (ADR-0004): the
    # instance_values ref is the source of truth, these two columns
    # answer "who owns this child" without a join. NULL on standalone
    # objects, scalar boxes and array instances.
    owner_object_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    owner_prop_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False, onupdate=func.now()
    )
