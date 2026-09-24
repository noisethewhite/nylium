"""TraitView — the wire projection of one trait (contracts.ts
TraitView): its own props plus the reverse attach list. Lives next to
the other schema views; there is no NyTrait domain facade to host it."""
from __future__ import annotations

from typing import Self

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.data.rows import Trait
from nylium.objects.navigation import (
    trait_attached_names,
    trait_color,
    trait_props,
)
from nylium.objects.nyprop import PropView

_CONFIG = ConfigDict(strict=True)


@dataclass(config=_CONFIG)
class TraitView:
    """One trait with its own props and reverse attach list
    (contracts.ts TraitView)."""

    name: str
    color: str
    props: list[PropView]
    attached: list[str]

    @classmethod
    def from_row(cls, trait: Trait) -> Self:
        return cls(
            name=trait.name,
            color=trait_color(trait.uuid),
            props=[PropView.from_row(prop) for prop in trait_props(trait.uuid)],
            attached=list(trait_attached_names(trait.uuid)),
        )
