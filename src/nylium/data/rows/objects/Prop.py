"""Prop mapped row."""
from __future__ import annotations

from typing import ClassVar, TypeAlias
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

SchemaItem: TypeAlias = (
    "tuple[UUID | None, str, UUID | None, UUID | None, str | None, str | None]"
)

@reg.mapped_as_dataclass
class Prop(Row):
    __tablename__: ClassVar[str] = "props"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint("owner_type_uuid", "key"),
        UniqueConstraint("owner_trait_uuid", "key"),
        CheckConstraint(
            "(owner_type_uuid IS NULL) <> (owner_trait_uuid IS NULL)",
            name="props_owner_exactly_one",
        ),
        CheckConstraint(
            "(value_type_uuid IS NULL) <> (value_trait_uuid IS NULL)",
            name="props_value_exactly_one",
        ),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=True, default=None
    )
    owner_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), nullable=True, default=None
    )
    value_type_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("types.uuid"), nullable=True, default=None
    )
    value_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="RESTRICT"), nullable=True, default=None
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    formula: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    collect: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
