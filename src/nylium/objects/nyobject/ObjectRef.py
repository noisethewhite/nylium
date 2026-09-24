from __future__ import annotations
from nylium.objects.nyobject.shared import CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str
