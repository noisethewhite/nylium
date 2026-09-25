from __future__ import annotations
from nylium.uuid import FunctionUUID
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionEdgeView:
    """A dataflow edge between two function nodes (ADR-0007)."""

    uuid: FunctionUUID
    from_node_uuid: FunctionUUID
    from_port: int
    to_node_uuid: FunctionUUID
    to_port: int
