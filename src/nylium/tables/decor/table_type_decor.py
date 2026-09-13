"""The decor row of one type (raw row mapping). uuid is both PK and FK — 1:1 with types."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_TypeDecor:
    """The decor row of one type. uuid is both PK and FK — 1:1 with types."""

    __tablename__: ClassVar[str] = "type_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    # plural display form; unique across types (moved from types in ADR-0014)
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Material Symbols name or `img:<uuid>` (ADR-0006), rendered by the UI
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    # #RRGGBB hex; the default must match WColor.DEFAULT
    # (tables must not import objects — keep the literal in sync by hand)
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )
