from __future__ import annotations
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionEdgeInput:
    """A dataflow edge between two node uuids in a DAG draft."""

    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int


resolve_route_hints(sys.modules[__name__])
