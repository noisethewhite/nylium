from __future__ import annotations
from nylium.objects.nyobject.shared import CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object]
