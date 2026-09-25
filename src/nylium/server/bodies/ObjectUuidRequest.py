from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.server.NotFoundError import NotFoundError
from nylium.ny.nyobject import ObjectView
from nylium.server.bodies.shared import PATH_PARAMS
from fastapi.responses import Response
from uuid import UUID
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class ObjectUuidRequest:
    """Path-bound input of the single-object routes."""

    object_uuid: UUID

    @classmethod
    def route_get(cls, request: Annotated["ObjectUuidRequest", PATH_PARAMS]) -> ObjectView:
        view = Api.get_object(request.object_uuid)
        if view is None:
            raise NotFoundError(f"no object {request.object_uuid}")
        return view

    @classmethod
    def route_delete(cls, request: Annotated["ObjectUuidRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_object(request.object_uuid):
            raise NotFoundError(f"no object {request.object_uuid}")
        return Response(status_code=204)

    @classmethod
    def route_export(cls, request: Annotated["ObjectUuidRequest", PATH_PARAMS]) -> Response:
        result = Api.export_markdown(request.object_uuid)
        if result is None:
            raise NotFoundError(f"no object {request.object_uuid}")
        filename, content = result
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


resolve_route_hints(sys.modules[__name__])
