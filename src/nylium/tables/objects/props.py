# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
# pyright: reportImportCycles=false
# Row navigation is bidirectional by design (Type.props <-> Prop.value_type);
# the back-edges are lazy function-level imports, so there is no runtime cycle.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
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
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
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
    owner_type_uuid: UUID
    value_type_uuid: UUID
    position: int
    formula: str | None
    function_uuid: UUID | None

    @property
    def value_type(self) -> str:
        """The value type's name — the wire-facing form of
        ``value_type_uuid``."""
        from nylium.tables.objects.types import types

        t = types.get(self.value_type_uuid)
        if t is None:
            raise KeyError(f"Type with UUID {self.value_type_uuid} does not exist")
        return t.name

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape: uuid/uuids as strings, matching
        web/src/contracts.ts PropView."""
        function_uuid = self.function_uuid
        return {
            "uuid": str(self.uuid),
            "key": self.key,
            "value_type": self.value_type,
            "formula": self.formula,
            "function_uuid": None if function_uuid is None else str(function_uuid),
        }


class Props(Table[UUID, Prop]):
    """The props table as a Mapping of writable props."""

    __row__: ClassVar[type[Row]] = Prop


props = Props()
