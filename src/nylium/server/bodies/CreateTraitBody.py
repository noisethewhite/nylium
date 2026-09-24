from __future__ import annotations
from nylium.api.Api import Api
from nylium.objects.NyColor import NyColor
from nylium.objects.TraitView import TraitView
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class CreateTraitBody:
    """A trait (ADR-0013): name, color, and a prop bundle — the same
    key -> value spec shape as CreateTypeBody.props."""

    name: str
    props: dict[str, str] = field(default_factory=dict)
    color: str = NyColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateTraitBody") -> TraitView:
        return TraitView.from_row(Api.create_trait(body.name, body.color, body.props))


resolve_route_hints(sys.modules[__name__])
