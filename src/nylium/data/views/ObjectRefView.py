from __future__ import annotations
from uuid import UUID
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class ObjectRefView:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str
