from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base
from nylium.tables.objects.typeref import TABLE_Types

# TABLE_Types comes from typeref.py, not types.py: types.py imports this
# module for the Type.props navigation property, so importing the domain
# layer back would cycle. Type-name resolution is a plain SQL select.


def _type_name_by_uuid(uuid: UUID) -> str | None:
    """A type row's name, or None when the uuid doesn't exist."""
    return Database.session.scalar(
        sqla.select(TABLE_Types.name).where(TABLE_Types.uuid == uuid)
    )


class TABLE_Props(Base):
    __tablename__: str = "props"
    __table_args__: tuple[UniqueConstraint, ...] = (
        # One key can't be defined twice on the same owner type
        UniqueConstraint("owner_type_uuid", "key"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
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
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-0007: a reference to a Function<T,R> instance whose output type
    # is this prop's value type; the result is computed lazily at read time
    # (like a formula). Mutually exclusive with `formula`.
    function_uuid: Mapped[UUID | None] = mapped_column(nullable=True)


class Prop(TableDomain):
    """One prop: a writable snapshot of a TABLE_Props row."""

    __table__: ClassVar[type[Base]] = TABLE_Props

    uuid: tableproperty[Prop, UUID] = tableproperty()
    key: tableproperty[Prop, str] = tableproperty()
    owner_type_uuid: tableproperty[Prop, UUID] = tableproperty()
    value_type_uuid: tableproperty[Prop, UUID] = tableproperty()
    position: tableproperty[Prop, int] = tableproperty()
    formula: tableproperty[Prop, str | None] = tableproperty()
    function_uuid: tableproperty[Prop, UUID | None] = tableproperty()

    @property
    def value_type(self) -> str:
        """The value type's name — the wire-facing form of
        ``value_type_uuid`` (the view the API used to build carried the
        name, not the uuid)."""
        with SessionContext():
            name = _type_name_by_uuid(self.value_type_uuid)
        if name is None:
            raise KeyError(f"Type with UUID {self.value_type_uuid} does not exist")
        return name

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape (ADR-0011 §5): uuid/uuids as strings,
        matching web/src/contracts.ts PropView."""
        function_uuid = self.function_uuid
        return {
            "uuid": str(self.uuid),
            "key": self.key,
            "value_type": self.value_type,
            "formula": self.formula,
            "function_uuid": None if function_uuid is None else str(function_uuid),
        }


class Props(TableMapping[UUID, Prop]):
    """The props table as a Mapping of writable props."""

    __domain__: ClassVar[type[TableDomain]] = Prop

    @databasemethod(commit=False)
    def update_formula(self, prop_uuid: UUID, formula: str) -> None:
        """Persist a rewritten formula string (ADR-0005 rename-rewrite)."""
        row = Database.session.get(TABLE_Props, prop_uuid)
        if row is None:
            raise KeyError(f"no prop {prop_uuid}")
        row.formula = formula

    @databasemethod(commit=False)
    def set_function(self, prop_uuid: UUID, function_uuid: UUID | None) -> None:
        """Bind (or unbind, with None) a Function<T,R> instance to a prop —
        the prop becomes function-backed and is computed at read time
        (ADR-0007). Mutually exclusive with `formula`; the caller validates."""
        row = Database.session.get(TABLE_Props, prop_uuid)
        if row is None:
            raise KeyError(f"no prop {prop_uuid}")
        row.function_uuid = function_uuid

    @databasemethod(commit=False)
    def clear_function_references(self, function_uuid: UUID) -> None:
        """Unbind every prop computed through this function — called before
        deleting the function instance so no prop strands a dangling uuid."""
        rows = Database.session.scalars(
            sqla.select(TABLE_Props).where(TABLE_Props.function_uuid == function_uuid)
        ).all()
        for row in rows:
            row.function_uuid = None


props = Props()
