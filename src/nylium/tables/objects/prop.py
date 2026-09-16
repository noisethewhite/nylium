# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
# pyright: reportImportCycles=false
# Row navigation is bidirectional by design (Type.props <-> Prop.value_type);
# the back-edges are lazy function-level imports, so there is no runtime cycle.
"""One prop: a writable snapshot of a TABLE_Props row (Row class only)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.table_props import TABLE_Props


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
    collect: str | None
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
