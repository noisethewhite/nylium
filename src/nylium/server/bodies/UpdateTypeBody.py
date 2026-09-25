from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.data.views.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class UpdateTypeBody:
    """PATCH semantics: only the listed fields change."""

    name: str | None = None
    plural_name: str | None = None
    icon: str | None = None
    color: str | None = None

    @classmethod
    def route(cls, name: str, body: "UpdateTypeBody") -> TypeView:
        return ApiShared.type_view(
            Api.rename_type(name, body.name, body.plural_name, body.icon, body.color)
        )


resolve_route_hints(sys.modules[__name__])
