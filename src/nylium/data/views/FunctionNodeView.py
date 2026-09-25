from __future__ import annotations
from nylium.uuid import FunctionUUID
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: FunctionUUID
    kind: str
    position: int
    config: dict[str, object]
