from __future__ import annotations
from nylium.uuid import FunctionRef
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: FunctionRef
    kind: str
    position: int
    config: dict[str, object]
