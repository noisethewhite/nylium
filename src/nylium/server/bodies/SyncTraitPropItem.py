from __future__ import annotations
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class SyncTraitPropItem:
    """One row of the trait editor's draft: uuid None = new prop.
    Traits v1 have no formulas — no formula field."""

    key: str
    value_type: str
    uuid: UUID | None = None


resolve_route_hints(sys.modules[__name__])
