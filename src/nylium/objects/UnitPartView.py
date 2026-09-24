from __future__ import annotations
from decimal import Decimal
from typing import Self
from uuid import UUID
from nylium.data.rows import UnitPart
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict


_VIEW_CONFIG = ConfigDict(strict=True)


@dataclass(config=_VIEW_CONFIG)
class UnitPartView:
    """One unit part (contracts.ts UnitPartView) — the wire projection,
    kept next to the domain facade it renders. Decimals cross as strings
    in pydantic JSON mode, losslessly."""

    uuid: UUID
    name: str
    multiplier: Decimal
    offset: Decimal
    is_base: bool

    @classmethod
    def from_row(cls, part: UnitPart) -> Self:
        return cls(
            uuid=part.uuid,
            name=part.name,
            multiplier=part.multiplier,
            offset=part.offset,
            is_base=part.is_base,
        )
