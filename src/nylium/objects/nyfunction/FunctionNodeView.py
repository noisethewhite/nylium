from __future__ import annotations
from uuid import UUID
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object]
