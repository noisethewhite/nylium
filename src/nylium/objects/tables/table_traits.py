"""The raw `traits` row mapping (ADR-0013)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg

# ADR-0013: a trait is a named, colored bundle of prop definitions.
# Attaching a trait to a type gives the type those props (the *effective*
# schema, see Type.props); the trait owns the prop rows, values stay
# keyed by (inst, prop) and don't care who owns the prop.


@reg.mapped_as_dataclass
class TABLE_Traits:
    __tablename__: ClassVar[str] = "traits"

    uuid: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, kw_only=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # ADR-0014: the trait's color lives in trait_decor (tables/decor),
    # 1:1 by uuid.
