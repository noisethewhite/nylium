from __future__ import annotations
from nylium.uuid import FunctionRef
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionEdgeView:
    """A dataflow edge between two function nodes (ADR-0007)."""

    uuid: FunctionRef
    from_node_uuid: FunctionRef
    from_port: int
    to_node_uuid: FunctionRef
    to_port: int
