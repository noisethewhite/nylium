from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.errors.NotFoundError import NotFoundError
from nylium.server.NyliumApp import NyliumApp
from nylium.server.bodies.shared import PATH_PARAMS
from fastapi.responses import Response
from nylium.data.views.TypeView import TypeView
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
@plain_dataclass
class TypeNameRequest:
    """Path-bound input of the single-type GET/DELETE routes."""
    name: str
    @classmethod
    @NyliumApp.api_route("/types/{name}", "GET")
    def route_get(cls, request: Annotated["TypeNameRequest", PATH_PARAMS]) -> TypeView:
        type_ = Api.get_type(request.name)
        if type_ is None:
            raise NotFoundError(f"no type {request.name!r}")
        return ApiShared.type_view(type_)
    @classmethod
    @NyliumApp.api_route("/types/{name}", "DELETE", status_code=NyliumApp.NO_CONTENT)
    def route_delete(cls, request: Annotated["TypeNameRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_type(request.name):
            raise NotFoundError(f"no type {request.name!r}")
        return Response(status_code=204)
resolve_route_hints(sys.modules[__name__])
