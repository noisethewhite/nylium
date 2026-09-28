from __future__ import annotations
from typing import Annotated
from nylium.api import Api
from nylium.data.views import FunctionView
from nylium.server.errors import NotFoundError
from nylium.server.bodies.shared import NO_CONTENT, PATH_PARAMS, api_route
from fastapi.responses import Response
from uuid import UUID
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
@plain_dataclass
class FunctionUuidRequest:
    """Path-bound input of the single-function routes."""
    function_uuid: UUID
    @classmethod
    @api_route("/functions/{function_uuid}", "GET")
    def route_get(cls, request: Annotated["FunctionUuidRequest", PATH_PARAMS]) -> FunctionView:
        view = Api.get_function(request.function_uuid)
        if view is None:
            raise NotFoundError(f"no function {request.function_uuid}")
        return view
    @classmethod
    @api_route("/functions/{function_uuid}", "DELETE", status_code=NO_CONTENT)
    def route_delete(cls, request: Annotated["FunctionUuidRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_function(request.function_uuid):
            raise NotFoundError(f"no function {request.function_uuid}")
        return Response(status_code=204)
resolve_route_hints(sys.modules[__name__])
