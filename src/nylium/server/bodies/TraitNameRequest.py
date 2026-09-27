from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.server.errors.NotFoundError import NotFoundError
from nylium.server.bodies.shared import NO_CONTENT, PATH_PARAMS, api_route
from fastapi.responses import Response
from nylium.data.views.TraitView import TraitView
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
@plain_dataclass
class TraitNameRequest:
    """Path-bound input of the single-trait GET/DELETE routes."""
    name: str
    @classmethod
    @api_route("/traits/{name}", "GET")
    def route_get(cls, request: Annotated["TraitNameRequest", PATH_PARAMS]) -> TraitView:
        trait = Api.get_trait(request.name)
        if trait is None:
            raise NotFoundError(f"no trait {request.name!r}")
        return TraitView.from_row(trait)
    @classmethod
    @api_route("/traits/{name}", "DELETE", status_code=NO_CONTENT)
    def route_delete(cls, request: Annotated["TraitNameRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_trait(request.name):
            raise NotFoundError(f"no trait {request.name!r}")
        return Response(status_code=204)
resolve_route_hints(sys.modules[__name__])
