from __future__ import annotations
from nylium.objects.nyformula import Formula
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FormulaRenderBody:
    """AST in, canonical text out — the block editor commits with this."""

    ast: dict[str, object] = field(default_factory=dict)

    @classmethod
    def route(cls, body: "FormulaRenderBody") -> dict[str, str]:
        return {"formula": Formula.from_dict(body.ast)}


resolve_route_hints(sys.modules[__name__])
