from __future__ import annotations
from nylium.data.rows import Prop
from typing import Self
from uuid import UUID
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants
from nylium.uuid import PropUUID




@dataclass(config=Constants.Pydantic.VIEW_CONFIG)
class PropView:
    """One prop of a type's effective schema (contracts.ts PropView) —
    the wire projection, kept next to the domain facade it renders."""

    uuid: UUID
    key: str
    value_type: str
    formula: str | None
    collect: str | None
    trait: str | None
    trait_color: str | None

    @classmethod
    def from_row(cls, prop: Prop) -> Self:
        owner_trait = PropUUID.of(prop.uuid).owner_trait()
        return cls(
            uuid=prop.uuid,
            key=prop.key,
            value_type=PropUUID.of(prop.uuid).value_type_name(),
            formula=prop.formula,
            collect=prop.collect,
            trait=None if owner_trait is None else owner_trait[0],
            trait_color=None if owner_trait is None else owner_trait[1],
        )
