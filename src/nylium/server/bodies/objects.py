"""Object request bodies and their routes (ADR-0017)."""
from __future__ import annotations

import sys

from dataclasses import dataclass as plain_dataclass, field
from typing import Annotated
from uuid import UUID
from fastapi.responses import Response
from pydantic.dataclasses import dataclass
from nylium.api.api import Api
from nylium.api.display import ObjectView, PropValue
from nylium.server.bodies.shared import BODY_CONFIG, PATH_PARAMS, resolve_route_hints
from nylium.server.codec import PropCodec
from nylium.server.errors import NotFoundError


@dataclass(config=BODY_CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, body: "CreateObjectBody") -> ObjectView:
        decoded = PropCodec.decode(body.type_name, body.props)
        return Api.create_object(body.type_name, decoded)


@dataclass(config=BODY_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, object_uuid: UUID, body: "UpdateObjectBody") -> ObjectView:
        view = Api.get_object(object_uuid)
        if view is None:
            raise NotFoundError(f"no object {object_uuid}")
        decoded = PropCodec.decode(view.type_name, body.props)
        return Api.update_object(object_uuid, decoded)


@plain_dataclass
class ListObjectsRequest:
    """Query-bound input of GET /objects (type_name filter)."""

    type_name: str

    @classmethod
    def route(cls, request: Annotated["ListObjectsRequest", PATH_PARAMS]) -> list[ObjectView]:
        return Api.list_objects(request.type_name)


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
