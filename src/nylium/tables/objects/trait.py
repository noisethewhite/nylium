# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One trait: a writable snapshot of a TABLE_Traits row (Row class only)."""
from __future__ import annotations

from collections.abc import Generator
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.props import Prop, props
from nylium.tables.objects.table_traits import TABLE_Traits
from nylium.tables.objects.type_traits import type_traits


class Trait(Row):
    """One trait: a writable snapshot of a TABLE_Traits row."""

    __table__: ClassVar[type[object]] = TABLE_Traits

    uuid: UUID
    name: str

    @property
    def color(self) -> str:
        """The trait's decor color (ADR-0014: 1:1 row in trait_decor)."""
        from nylium.tables.decor import trait_decor

        decor = trait_decor.get(self.uuid)
        if decor is None:
            raise KeyError(f"trait {self.uuid} has no decor row")
        return decor.color

    @property
    def props(self) -> Generator[Prop, None, None]:
        """This trait's props, in display order."""
        yield from sorted(
            props.where(owner_trait_uuid=self.uuid), key=lambda p: p.position
        )

    @property
    def attached(self) -> Generator[str, None, None]:
        """Names of types this trait is attached to, in attach order."""
        from nylium.tables.objects.types import types

        links = sorted(
            type_traits.where(trait_uuid=self.uuid), key=lambda link: link.position
        )
        for link in links:
            owner = types.get(link.type_uuid)
            if owner is not None:
                yield owner.name
