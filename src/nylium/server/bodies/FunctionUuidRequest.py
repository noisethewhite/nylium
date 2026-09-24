from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.objects.nyfunction.FunctionView import FunctionView
from nylium.server.NotFoundError import NotFoundError
from nylium.server.bodies.shared import PATH_PARAMS
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
    def route_get(cls, request: Annotated["FunctionUuidRequest", PATH_PARAMS]) -> FunctionView:
        view = Api.get_function(request.function_uuid)
        if view is None:
            raise NotFoundError(f"no function {request.function_uuid}")
        return view

    @classmethod
    def route_delete(cls, request: Annotated["FunctionUuidRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_function(request.function_uuid):
            raise NotFoundError(f"no function {request.function_uuid}")
        return Response(status_code=204)


resolve_route_hints(sys.modules[__name__])
