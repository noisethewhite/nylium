"""Trait mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class Trait(Row):
    """One trait: a named, colored bundle of prop definitions (ADR-0013).

    The color lives in the 1:1 trait_style row (ADR-0014); cross-table
    navigation lives in ``nylium.ny.navigation``.
    """

    __tablename__: ClassVar[str] = "traits"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
