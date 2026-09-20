# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One type: a writable snapshot of a TABLE_Types row (Row class only)."""
from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.enum_options import EnumOption, enum_options
from nylium.tables.objects.props import Prop, props
from nylium.tables.objects.traits import Trait, traits, type_traits
from nylium.tables.objects.table_types import TABLE_Types
from nylium.tables.objects.unit_parts import UnitPart, unit_parts

if TYPE_CHECKING:
    from nylium.tables.decor import TypeDecor


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
    kind: str
    embedded: bool

    @property
    def _decor(self) -> TypeDecor:
        """ADR-0014: the 1:1 decor row — plural_name/icon/color."""
        from nylium.tables.decor import type_decor

        decor = type_decor.get(self.uuid)
        if decor is None:
            raise KeyError(f"type {self.uuid} has no decor row")
        return decor

    @property
    def plural_name(self) -> str:
        return self._decor.plural_name

    @property
    def icon(self) -> str:
        return self._decor.icon

    @property
    def color(self) -> str:
        return self._decor.color

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
