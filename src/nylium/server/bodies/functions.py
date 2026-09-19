"""Function request bodies and their routes (ADR-0007, ADR-0017)."""
from __future__ import annotations

import sys

from dataclasses import dataclass as plain_dataclass, field
from typing import Annotated
from uuid import UUID
from fastapi.responses import Response
from pydantic.dataclasses import dataclass
from nylium.api.api import Api
from nylium.api.display import FunctionView, ObjectView
from nylium.server.bodies.shared import BODY_CONFIG, PATH_PARAMS, resolve_route_hints
from nylium.server.errors import NotFoundError


@dataclass(config=BODY_CONFIG)
class FunctionNodeInput:
    """One node of a function's action DAG draft (ADR-0007). The client
    generates the uuid so edges can reference not-yet-created nodes."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object] = field(default_factory=dict)


@dataclass(config=BODY_CONFIG)
class FunctionEdgeInput:
    """A dataflow edge between two node uuids in a DAG draft."""

    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int


@dataclass(config=BODY_CONFIG)
class CreateFunctionBody:
    """A Function<T,R> instance (ADR-0029): parameterization + the full
    action DAG in one draft. No input link — the function reads the sibling
    props of the object it is bound into."""

    input_type: str
    output_type: str
    name: str
    nodes: list[FunctionNodeInput] = field(default_factory=list)
    edges: list[FunctionEdgeInput] = field(default_factory=list)

    @classmethod
    def route(cls, body: "CreateFunctionBody") -> FunctionView:
        return Api.create_function(
            body.input_type,
            body.output_type,
            body.name,
            [(n.uuid, n.kind, n.position, n.config) for n in body.nodes],
            [
                (e.from_node_uuid, e.from_port, e.to_node_uuid, e.to_port)
                for e in body.edges
            ],
        )


@dataclass(config=BODY_CONFIG)
class UpdateFunctionBody:
    """Replace a function's name and DAG (full-draft PUT semantics — the
    input/output parameterization is fixed)."""

    name: str
    nodes: list[FunctionNodeInput] = field(default_factory=list)
    edges: list[FunctionEdgeInput] = field(default_factory=list)

    @classmethod
    def route(cls, function_uuid: UUID, body: "UpdateFunctionBody") -> FunctionView:
        return Api.update_function(
            function_uuid,
            body.name,
            [(n.uuid, n.kind, n.position, n.config) for n in body.nodes],
            [
                (e.from_node_uuid, e.from_port, e.to_node_uuid, e.to_port)
                for e in body.edges
            ],
        )


@plain_dataclass
class ListFunctionsRequest:
    """No-input request of GET /functions."""

    @classmethod
    def route(cls, _request: Annotated["ListFunctionsRequest", PATH_PARAMS]) -> list[FunctionView]:
        return Api.list_functions()


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


@dataclass(config=BODY_CONFIG)
class SetInstancePropFunctionBody:
    """ADR-0029: bind a Function<T,R> to a prop of a specific object (None
    unbinds)."""

    function_uuid: UUID | None = None

    @classmethod
    def route(
        cls, object_uuid: UUID, prop_key: str, body: "SetInstancePropFunctionBody"
    ) -> ObjectView:
        return Api.set_instance_prop_function(object_uuid, prop_key, body.function_uuid)


resolve_route_hints(sys.modules[__name__])
