from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.objects.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class TraitAttachBody:
    """Attach/detach a trait to/from a type."""

    trait: str

    @classmethod
    def route(cls, name: str, body: "TraitAttachBody") -> TypeView:
        return ApiShared.type_view(Api.attach_trait(name, body.trait))


resolve_route_hints(sys.modules[__name__])
