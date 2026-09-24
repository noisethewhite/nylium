from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.objects.nyobject import ObjectView
from nylium.server.bodies.shared import PATH_PARAMS
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class ListObjectsRequest:
    """Query-bound input of GET /objects (type_name filter)."""

    type_name: str

    @classmethod
    def route(cls, request: Annotated["ListObjectsRequest", PATH_PARAMS]) -> list[ObjectView]:
        return Api.list_objects(request.type_name)


resolve_route_hints(sys.modules[__name__])
