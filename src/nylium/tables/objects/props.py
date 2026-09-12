# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
# pyright: reportImportCycles=false
# Row navigation is bidirectional by design (Type.props <-> Prop.value_type);
# the back-edges are lazy function-level imports, so there is no runtime cycle.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row, Table
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
    # ADR-0007: a reference to a Function<T,R> instance whose output type
    # is this prop's value type; the result is computed lazily at read time
    # (like a formula). Mutually exclusive with `formula`.
    function_uuid: Mapped[UUID | None] = mapped_column(nullable=True, default=None)


class Prop(Row):
    """One prop: a writable snapshot of a TABLE_Props row."""

    __table__: ClassVar[type[object]] = TABLE_Props

    uuid: UUID
    key: str
    owner_type_uuid: UUID | None
    owner_trait_uuid: UUID | None
    value_type_uuid: UUID | None
    value_trait_uuid: UUID | None
    position: int
    formula: str | None
    function_uuid: UUID | None

    @property
    def owner_trait(self) -> "tuple[str, str] | None":
        """(name, color) of the owning trait, None for a type-owned prop."""
        if self.owner_trait_uuid is None:
            return None
        from nylium.tables.objects.traits import traits

        t = traits.get(self.owner_trait_uuid)
        if t is None:
            raise KeyError(f"Trait with UUID {self.owner_trait_uuid} does not exist")
        return t.name, t.color

    @property
    def value_type(self) -> str:
        """The wire-facing value spec: the concrete type's name, or
        ``Any<TraitName>`` for a trait-bound prop (ADR-0013)."""
        if self.value_trait_uuid is not None:
            from nylium.tables.objects.traits import traits

            t = traits.get(self.value_trait_uuid)
            if t is None:
                raise KeyError(f"Trait with UUID {self.value_trait_uuid} does not exist")
            return f"Any<{t.name}>"
        if self.value_type_uuid is None:
            raise KeyError(f"Prop {self.key!r} has no value typing")
        from nylium.tables.objects.types import types

        t = types.get(self.value_type_uuid)
        if t is None:
            raise KeyError(f"Type with UUID {self.value_type_uuid} does not exist")
        return t.name

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape: uuid/uuids as strings, matching
        web/src/contracts.ts PropView."""
        function_uuid = self.function_uuid
        owner_trait = self.owner_trait
        return {
            "uuid": str(self.uuid),
            "key": self.key,
            "value_type": self.value_type,
            "formula": self.formula,
            "function_uuid": None if function_uuid is None else str(function_uuid),
            "trait": None if owner_trait is None else owner_trait[0],
            "trait_color": None if owner_trait is None else owner_trait[1],
        }


class Props(Table[UUID, Prop]):
    """The props table as a Mapping of writable props."""

    __row__: ClassVar[type[Row]] = Prop


props = Props()
