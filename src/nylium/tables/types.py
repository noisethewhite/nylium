from collections.abc import Generator
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base


class TABLE_Types(Base):
    """The raw `types` row — a plain mapped class, no behaviour (ADR-0011).

    Writers go through the ``Type`` domain object or the ``Types`` mapping
    below (``create``/``update``/``delete``), never by constructing
    ``TABLE_Types`` directly. The mapped class stays importable where a SQL
    join needs the table — that is its only legitimate public use.
    """

    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # NULL for builtins and array types — only user types carry both forms
    plural_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Material Symbols name, rendered monochrome by the UI;
    # server defaults backfill existing rows on ALTER
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    # ADR-0005: stores #RRGGBB hex; the default must match WColor.DEFAULT
    # (tables must not import objects — keep the literal in sync by hand)
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )
    # "object" (regular, builtin or array) | "enum" (string enum — its
    # values live in enum_options; instances never exist for enum types)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="object", server_default="object"
    )
    # Composition flag (ADR-0004): embedded types instantiate only as a
    # prop value of an owner object, never standalone. Orthogonal to
    # kind — an embedded type is still kind="object".
    embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Type(TableDomain):
    """One type: a writable snapshot of a TABLE_Types row."""

    __table__: ClassVar[type[Base]] = TABLE_Types

    uuid: tableproperty[UUID] = tableproperty()
    name: tableproperty[str] = tableproperty()
    plural_name: tableproperty[str | None] = tableproperty()
    icon: tableproperty[str] = tableproperty()
    color: tableproperty[str] = tableproperty()
    kind: tableproperty[str] = tableproperty()
    embedded: tableproperty[bool] = tableproperty()


class Types(TableMapping[UUID, Type]):
    """The types table as a Mapping of writable types."""

    __domain__: ClassVar[type[TableDomain]] = Type

    def all(self) -> Generator[Type, None, None]:
        """Every type, lazily."""
        with SessionContext():
            all_types = [
                cast(Type, Type.from_row(row))
                for row in Database.session.scalars(sqla.select(TABLE_Types))
            ]
        yield from all_types

    @databasemethod(commit=False)
    def by_name(self, name: str) -> Type | None:
        row = Database.session.scalar(
            sqla.select(TABLE_Types).where(TABLE_Types.name == name)
        )
        if row is None:
            return None
        return cast(Type, Type.from_row(row))

    @databasemethod(commit=True)
    def create(
        self,
        name: str,
        plural_name: str | None = None,
        icon: str | None = None,
        kind: str | None = None,
        embedded: bool | None = None,
    ) -> Type:
        row = TABLE_Types(name=name, plural_name=plural_name)
        if icon is not None:
            row.icon = icon
        if kind is not None:
            row.kind = kind
        if embedded is not None:
            row.embedded = embedded
        Database.session.add(row)
        Database.session.flush()
        return cast(Type, Type.from_row(row))

    @databasemethod(commit=True)
    def update(
        self,
        uuid: UUID,
        name: str,
        plural_name: str | None,
        icon: str,
        color: str,
    ) -> None:
        row = Database.session.get(TABLE_Types, uuid)
        if row is None:
            raise KeyError(f"no type with uuid {uuid}")
        row.name = name
        row.plural_name = plural_name
        row.icon = icon
        row.color = color
        Database.session.flush()

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Types, uuid)
        if row is not None:
            Database.session.delete(row)  # its props cascade


types = Types()
