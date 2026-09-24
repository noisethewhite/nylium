from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.objects.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class ReorderPropsBody:
    """New ordering for a type's props, as a full list of prop keys."""

    keys: list[str]

    @classmethod
    def route(cls, name: str, body: "ReorderPropsBody") -> TypeView:
        return ApiShared.type_view(Api.reorder_props(name, body.keys))


resolve_route_hints(sys.modules[__name__])
