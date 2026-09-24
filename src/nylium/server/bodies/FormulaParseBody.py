from __future__ import annotations
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.objects.nyformula import Formula
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class FormulaParseBody:
    """Text in, AST out — the block editor opens a stored formula with this."""

    formula: str

    @classmethod
    def route(cls, body: "FormulaParseBody") -> dict[str, object]:
        return {"ast": Formula.to_dict(body.formula)}


resolve_route_hints(sys.modules[__name__])
