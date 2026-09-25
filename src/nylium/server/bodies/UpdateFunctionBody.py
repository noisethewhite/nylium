from __future__ import annotations
from nylium.api.Api import Api
from nylium.server.bodies.FunctionEdgeInput import FunctionEdgeInput
from nylium.server.bodies.FunctionNodeInput import FunctionNodeInput
from nylium.data.views.FunctionView import FunctionView
from uuid import UUID
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
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


resolve_route_hints(sys.modules[__name__])
