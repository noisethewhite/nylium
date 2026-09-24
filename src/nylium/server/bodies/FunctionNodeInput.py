from __future__ import annotations
from uuid import UUID
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionNodeInput:
    """One node of a function's action DAG draft (ADR-0007). The client
    generates the uuid so edges can reference not-yet-created nodes."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object] = field(default_factory=dict)


resolve_route_hints(sys.modules[__name__])
