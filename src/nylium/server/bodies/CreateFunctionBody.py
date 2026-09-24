from __future__ import annotations
from nylium.api.Api import Api
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.server.bodies.FunctionEdgeInput import FunctionEdgeInput
from nylium.server.bodies.FunctionNodeInput import FunctionNodeInput
from nylium.objects.nyfunction.FunctionView import FunctionView
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints


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


resolve_route_hints(sys.modules[__name__])
