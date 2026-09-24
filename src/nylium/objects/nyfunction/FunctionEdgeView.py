from __future__ import annotations
from nylium.objects.nyobject.shared import CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class FunctionEdgeView:
    """A dataflow edge between two function nodes (ADR-0007)."""

    uuid: UUID
    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int
