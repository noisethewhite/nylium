"""TraitUUID — typed identifier for a ``Trait`` row (``traits``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import Prop, Trait
from nylium.data.tables import props, trait_decor, traits, type_traits, types


class TraitUUID(UUID):
    """A ``traits`` uuid carrying its own table lookup and navigation."""

    @classmethod
    def of(cls, value: UUID) -> "TraitUUID":
        return cls(str(value))

    def get(self) -> Trait | None:
        """The ``Trait`` row this uuid points at, or ``None`` if it is gone."""
        return traits.get(self)

    def color(self) -> str:
        return trait_decor[self].color

    def props(self) -> list[Prop]:
        return sorted(props.where(owner_trait_uuid=self), key=lambda p: p.position)

    def attached_names(self) -> list[str]:
        """Names of types this trait is attached to, in attach order."""
        result: list[str] = []
        for link in sorted(type_traits.where(trait_uuid=self), key=lambda link: link.position):
            owner = types.get(link.type_uuid)
            if owner is not None:
                result.append(owner.name)
        return result
