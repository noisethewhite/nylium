"""Which trait is attached to which type, in attach order (raw row mapping)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_TypeTraits:
    """Which trait is attached to which type, in attach order."""

    __tablename__: ClassVar[str] = "type_traits"

    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    trait_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    # trait prop groups render after the type's own props, in this order
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
