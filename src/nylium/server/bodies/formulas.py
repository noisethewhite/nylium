"""Formula AST endpoints (ADR-0026): text ⇄ block-editor AST JSON."""
from __future__ import annotations

import sys
from dataclasses import field

from pydantic.dataclasses import dataclass

from nylium.objects.nyformula import Formula
from nylium.server.bodies.shared import BODY_CONFIG, resolve_route_hints


@dataclass(config=BODY_CONFIG)
class FormulaParseBody:
    """Text in, AST out — the block editor opens a stored formula with this."""

    formula: str

    @classmethod
    def route(cls, body: "FormulaParseBody") -> dict[str, object]:
        return {"ast": Formula.to_dict(body.formula)}


@dataclass(config=BODY_CONFIG)
class FormulaRenderBody:
    """AST in, canonical text out — the block editor commits with this."""

    ast: dict[str, object] = field(default_factory=dict)

    @classmethod
    def route(cls, body: "FormulaRenderBody") -> dict[str, str]:
        return {"formula": Formula.from_dict(body.ast)}


resolve_route_hints(sys.modules[__name__])
