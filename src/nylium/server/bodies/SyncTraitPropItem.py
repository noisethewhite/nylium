from __future__ import annotations
from nylium.server.bodies.shared import BODY_CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class SyncTraitPropItem:
    """One row of the trait editor's draft: uuid None = new prop.
    Traits v1 have no formulas — no formula field."""

    key: str
    value_type: str
    uuid: UUID | None = None


resolve_route_hints(sys.modules[__name__])
