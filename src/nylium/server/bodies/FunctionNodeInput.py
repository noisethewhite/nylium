from __future__ import annotations
from nylium.server.bodies.shared import BODY_CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class FunctionNodeInput:
    """One node of a function's action DAG draft (ADR-0007). The client
    generates the uuid so edges can reference not-yet-created nodes."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object] = field(default_factory=dict)


resolve_route_hints(sys.modules[__name__])
