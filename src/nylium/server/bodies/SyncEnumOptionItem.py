from __future__ import annotations
from nylium.server.bodies.shared import BODY_CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class SyncEnumOptionItem:
    """One row of the enum editor's draft: uuid None = new option."""

    value: str
    uuid: UUID | None = None


resolve_route_hints(sys.modules[__name__])
