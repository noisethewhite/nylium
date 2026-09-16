"""The raw `props` row mapping (ADR-0013)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg

# TABLE_Types is not imported here: types.py imports this module for the
# Type.props navigation, so importing the domain layer back at module level
# would cycle. Prop.value_type lazy-imports ``types``.


@reg.mapped_as_dataclass
class TABLE_Props:
    __tablename__: ClassVar[str] = "props"
    __table_args__: ClassVar[tuple[object, ...]] = (
        # One key can't be defined twice on the same owner type
        UniqueConstraint("owner_type_uuid", "key"),
        # ...nor twice on the same owner trait (ADR-0013); NULL owners are
        # distinct in Postgres, so each constraint guards its own kind
        UniqueConstraint("owner_trait_uuid", "key"),
        # a prop belongs to exactly one owner: one type XOR one trait
        CheckConstraint(
            "(owner_type_uuid IS NULL) <> (owner_trait_uuid IS NULL)",
            name="props_owner_exactly_one",
        ),
        # ...and its value is exactly one concrete type XOR one trait bound
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
    # ADR-0013: the alternative owner — a trait
    owner_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), nullable=True, default=None
    )
    value_type_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("types.uuid"), nullable=True, default=None
    )
    # ADR-0013: the alternative value typing — any object whose type has
    # this trait (wire form "Any<TraitName>"). RESTRICT: a trait still
    # used as a bound can't be deleted silently
    value_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="RESTRICT"), nullable=True, default=None
    )
    # the prop's slot in the owner type's display order — create order
    # unless a reorder overwrote it
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # ADR-0005: a formula string over the owner's Array<T> props (e.g.
    # "SUM(items.price) * 1.21"); NULL means a plain stored prop
    formula: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # ADR-0025: a collect spec — the key of an ordered scalar member prop on
    # this Array<T>'s element type. The array is derived at read time as every
    # element whose member prop falls within the owner's [from, to] bounds.
    collect: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # ADR-0007: a reference to a Function<T,R> instance whose output type
    # is this prop's value type; the result is computed lazily at read time
    # (like a formula). Mutually exclusive with `formula`.
    function_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
