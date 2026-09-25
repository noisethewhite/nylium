from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.ny.NyColor import NyColor
from nylium.data.views.TypeView import TypeView
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class CreateEnumBody:
    """A string enum type: name plus its allowed option values."""

    name: str
    options: list[str] = field(default_factory=list)
    icon: str = "lists"
    color: str = NyColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateEnumBody") -> TypeView:
        return ApiShared.type_view(
            Api.create_enum(body.name, body.options, body.icon, body.color)
        )


resolve_route_hints(sys.modules[__name__])
