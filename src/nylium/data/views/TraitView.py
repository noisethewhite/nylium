"""TraitView — the wire projection of one trait (contracts.ts
TraitView): its own props plus the reverse attach list. Lives next to
the other schema views; there is no NyTrait domain facade to host it."""
from __future__ import annotations

from typing import Self

from nylium.Constants import Constants
from pydantic.dataclasses import dataclass

from nylium.data.rows import Trait
from nylium.uuid import TraitUUID
from nylium.data.views.PropView import PropView



@dataclass(config=Constants.Pydantic.VIEW_CONFIG)
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
            color=TraitUUID.of(trait.uuid).color(),
            props=[PropView.from_row(prop) for prop in TraitUUID.of(trait.uuid).props()],
            attached=list(TraitUUID.of(trait.uuid).attached_names()),
        )
