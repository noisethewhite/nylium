"""The decor row of one trait (ADR-0013 traits carry only a color)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_TraitDecor:
    """The decor row of one trait (ADR-0013 traits carry only a color)."""

    __tablename__: ClassVar[str] = "trait_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    color: Mapped[str] = mapped_column(Text, nullable=False)
