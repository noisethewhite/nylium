from __future__ import annotations
from decimal import Decimal
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class UnitSecondaryInput:
    """One secondary part of a new unit: name and the affine conversion
    factor (base = (entered - offset) / multiplier)."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)


resolve_route_hints(sys.modules[__name__])
