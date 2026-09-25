"""Type mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class Type(Row):
    """One type: identity + semantics (ADR-0014 keeps decor in type_style).

    Cross-table navigation (props/traits/decor) lives in
    ``nylium.ny.navigation`` — a Row never imports a sibling table.
    """

    __tablename__: ClassVar[str] = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="object", server_default="object"
    )
    embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
