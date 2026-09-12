# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from collections.abc import Generator
from typing import ClassVar
from uuid import UUID

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.objects.enum_options import EnumOption, enum_options
from nylium.tables.objects.props import Prop, props
from nylium.tables.objects.traits import Trait, traits, type_traits
from nylium.tables.objects.typeref import TABLE_Types
from nylium.tables.objects.unit_parts import UnitPart, unit_parts

__all__ = ["TABLE_Types", "Type", "Types", "types"]

# TABLE_Types lives in typeref.py (see that module's docstring) and is
# re-exported here: `from nylium.tables.objects.types import TABLE_Types` keeps
# working everywhere.


class Type(Row):
    """One type: a writable snapshot of a TABLE_Types row.

    The row carries the aggregate navigations — ``props`` /
    ``enum_options`` / ``unit_parts`` reach into the child tables. This
    module is the top of the tables import DAG: the child modules
    lazy-import ``types`` where they need it, never at module level.
    """

    __table__: ClassVar[type[object]] = TABLE_Types

    uuid: UUID
    name: str
    plural_name: str
    icon: str
    color: str
    kind: str
    embedded: bool

    @property
    def own_props(self) -> Generator[Prop, None, None]:
        """The props this type owns directly, in display order (ADR-0013:
        writes — sync_schema — always target own props only)."""
        yield from sorted(props.where(owner_type_uuid=self.uuid), key=lambda p: p.position)

    @property
    def traits(self) -> Generator[Trait, None, None]:
        """Traits attached to this type, in attach order."""
        links = sorted(
            type_traits.where(type_uuid=self.uuid), key=lambda link: link.position
        )
        for link in links:
            trait = traits.get(link.trait_uuid)
            if trait is not None:
                yield trait

    @property
    def props(self) -> Generator[Prop, None, None]:
        """The *effective* schema (ADR-0013): own props, then each attached
        trait's props in attach order."""
        yield from self.own_props
        for trait in self.traits:
            yield from trait.props

    @property
    def enum_options(self) -> Generator[EnumOption, None, None]:
        """This enum's options, in display order (empty for non-enums)."""
        yield from sorted(
            enum_options.where(type_uuid=self.uuid), key=lambda o: o.position
        )

    @property
    def unit_parts(self) -> Generator[UnitPart, None, None]:
        """This unit's parts, in display order (empty for non-units)."""
        yield from sorted(
            unit_parts.where(type_uuid=self.uuid), key=lambda p: p.position
        )

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape, matching web/src/contracts.ts TypeView."""
        return {
            "name": self.name,
            "plural_name": self.plural_name,
            "icon": self.icon,
            "color": self.color,
            "kind": self.kind,
            "embedded": self.embedded,
            "traits": [trait.name for trait in self.traits],
            "enum_options": [option.wire() for option in self.enum_options],
            "unit_parts": [part.wire() for part in self.unit_parts],
            "props": [prop.wire() for prop in self.props],
        }


class Types(Table[UUID, Type]):
    """The types table as a Mapping of writable types."""

    __row__: ClassVar[type[Row]] = Type

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
        return Type(row)

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Types, uuid)
        if row is not None:
            Database.session.delete(row)  # its props cascade


types = Types()
