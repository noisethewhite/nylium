from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class SyncUnitPartItem:
    """One row of the unit editor's draft: uuid None = new part."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)
    is_base: bool = False
    uuid: UUID | None = None


resolve_route_hints(sys.modules[__name__])
