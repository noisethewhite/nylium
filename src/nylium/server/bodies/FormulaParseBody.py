from __future__ import annotations
from nylium.ny.nyformula import Formula
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import api_route, resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FormulaParseBody:
    """Text in, AST out — the block editor opens a stored formula with this."""

    formula: str

    @classmethod
    @api_route("/formulas/parse", "POST")
    def route(cls, body: "FormulaParseBody") -> dict[str, object]:
        return {"ast": Formula.to_dict(body.formula)}


resolve_route_hints(sys.modules[__name__])
