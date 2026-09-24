from __future__ import annotations
from nylium.data.rows import EnumOption
from typing import Self
from uuid import UUID
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict


_VIEW_CONFIG = ConfigDict(strict=True)


@dataclass(config=_VIEW_CONFIG)
class EnumOptionView:
    """One enum option (contracts.ts EnumOptionView) — the wire
    projection, kept next to the domain facade it renders."""

    uuid: UUID
    value: str

    @classmethod
    def from_row(cls, option: EnumOption) -> Self:
        return cls(uuid=option.uuid, value=option.value)
