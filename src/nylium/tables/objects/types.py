from __future__ import annotations

from collections.abc import Generator
from typing import ClassVar, cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base
from nylium.tables.objects.enum_options import EnumOption
from nylium.tables.objects.props import Prop
from nylium.tables.objects.typeref import TABLE_Types
from nylium.tables.objects.unit_parts import UnitPart

__all__ = ["TABLE_Types", "Type", "Types", "types"]

# TABLE_Types lives in typeref.py (see that module's docstring) and is
# re-exported here: `from nylium.tables.objects.types import TABLE_Types` keeps
# working everywhere.


class Type(TableDomain):
    """One type: a writable snapshot of a TABLE_Types row.

    ADR-0011 §5: the domain object carries the aggregate fields the old
    TypeView carried — ``props``/``enum_options``/``unit_parts`` navigate
    to the child tables. This module is the top of the tables import DAG:
    the child modules lazy-import ``types`` where they need it, never at
    module level."""

    __table__: ClassVar[type[Base]] = TABLE_Types

    uuid: tableproperty[Type, UUID] = tableproperty()
    name: tableproperty[Type, str] = tableproperty()
    plural_name: tableproperty[Type, str] = tableproperty()
    icon: tableproperty[Type, str] = tableproperty()
    color: tableproperty[Type, str] = tableproperty()
    kind: tableproperty[Type, str] = tableproperty()
    embedded: tableproperty[Type, bool] = tableproperty()

    @property
    def props(self) -> list[Prop]:
        """This type's props, in display order."""
        return sorted(
            Prop.owner_type_uuid.foreach(self.uuid), key=lambda prop: prop.position
        )

    @property
    def enum_options(self) -> list[EnumOption]:
        """This enum's options, in display order (empty for non-enums)."""
        return sorted(
            EnumOption.type_uuid.foreach(self.uuid), key=lambda option: option.position
        )

    @property
    def unit_parts(self) -> list[UnitPart]:
        """This unit's parts, in display order (empty for non-units)."""
        return sorted(
            UnitPart.type_uuid.foreach(self.uuid), key=lambda part: part.position
        )

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape (ADR-0011 §5), matching
        web/src/contracts.ts TypeView."""
        return {
            "name": self.name,
            "plural_name": self.plural_name,
            "icon": self.icon,
            "color": self.color,
            "kind": self.kind,
            "embedded": self.embedded,
            "enum_options": [option.wire() for option in self.enum_options],
            "unit_parts": [part.wire() for part in self.unit_parts],
            "props": [prop.wire() for prop in self.props],
        }


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

    @databasemethod(commit=True)
    def create(
        self,
        name: str,
        plural_name: str,
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
        plural_name: str,
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
