"""TraitRef — typed reference to a ``Trait`` row (``traits``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import Prop, Trait
from nylium.data.tables import props, trait_style, traits, type_traits, types
from nylium.uuid.NyRef import NyRef


class TraitRef(NyRef):
    """A ``traits`` reference carrying its own table lookup and navigation."""

    @override
    def get(self) -> Trait | None:
        """The ``Trait`` row this reference points at, or ``None`` if it is gone."""
        return traits.get(self._uuid)

    def color(self) -> str:
        return trait_style[self._uuid].color

    def props(self) -> list[Prop]:
        return sorted(props.where(owner_trait_uuid=self._uuid), key=lambda p: p.position)

    def attached_names(self) -> list[str]:
        """Names of types this trait is attached to, in attach order."""
        result: list[str] = []
        for link in sorted(type_traits.where(trait_uuid=self._uuid), key=lambda link: link.position):
            owner = types.get(link.type_uuid)
            if owner is not None:
                result.append(owner.name)
        return result
