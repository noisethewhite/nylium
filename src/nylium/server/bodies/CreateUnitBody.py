from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.objects.NyColor import NyColor
from nylium.objects.TypeView import TypeView
from nylium.server.bodies.UnitSecondaryInput import UnitSecondaryInput
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class CreateUnitBody:
    """A unit type: name, its base part, and optional secondary parts."""

    name: str
    base: str
    secondaries: list[UnitSecondaryInput] = field(default_factory=list)
    icon: str = "straighten"
    color: str = NyColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateUnitBody") -> TypeView:
        return ApiShared.type_view(
            Api.create_unit(
                body.name,
                body.base,
                [
                    (item.name, item.multiplier, item.offset)
                    for item in body.secondaries
                ],
                body.icon,
                body.color,
            )
        )


resolve_route_hints(sys.modules[__name__])
