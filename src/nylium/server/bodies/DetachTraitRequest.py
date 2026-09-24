from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.shared import PATH_PARAMS
from nylium.objects.TypeView import TypeView
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class DetachTraitRequest:
    """Path-bound input of DELETE /types/{name}/traits/{trait}."""

    name: str
    trait: str

    @classmethod
    def route(cls, request: Annotated["DetachTraitRequest", PATH_PARAMS]) -> TypeView:
        return ApiShared.type_view(Api.detach_trait(request.name, request.trait))


resolve_route_hints(sys.modules[__name__])
