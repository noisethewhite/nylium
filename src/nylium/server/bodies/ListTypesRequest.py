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
class ListTypesRequest:
    """No-input request of GET /types."""

    @classmethod
    def route(cls, _request: Annotated["ListTypesRequest", PATH_PARAMS]) -> list[TypeView]:
        return ApiShared.type_views(Api.list_types())


resolve_route_hints(sys.modules[__name__])
