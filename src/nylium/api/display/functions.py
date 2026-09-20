"""The Function<T,R> projections (ADR-0007): node/edge DTOs of the
action DAG and FunctionView, a full snapshot of one function instance."""
from __future__ import annotations

from typing import Self, cast
from uuid import UUID

from pydantic.dataclasses import dataclass

from nylium.database import use_same_session
from nylium.objects.tables import instances
from nylium.objects import WObject, WType
from nylium.objects.wfunction import WFunction
from nylium.api.display.values import CONFIG, NAME_PROP_KEY


@dataclass(config=CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object]


@dataclass(config=CONFIG)
class FunctionEdgeView:
    """A dataflow edge between two function nodes (ADR-0007)."""

    uuid: UUID
    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int


@dataclass(config=CONFIG)
class FunctionView:
    """Snapshot of one Function<T,R> instance: its parameterization and its
    full action DAG (nodes + edges). ADR-0029: no input link — the input is
    the sibling props of the object the function is bound into."""

    uuid: UUID
    name: str
    type_name: str
    input_type: str
    output_type: str
    nodes: list[FunctionNodeView]
    edges: list[FunctionEdgeView]

    @classmethod
    @use_same_session
    def from_uuid(cls, uuid: UUID) -> Self | None:
        inst = instances.get(uuid)
        type_uuid = None if inst is None else inst.type_uuid
        if type_uuid is None:
            return None
        owner = WType.by_uuid(type_uuid)
        if owner is None or not owner.is_function:
            return None
        params = WType.function_params(owner.name)
        if params is None:
            return None
        input_type, output_type = params
        wrapper = WObject.wrap(uuid)
        name = cast(str | None, getattr(wrapper, NAME_PROP_KEY))
        if not name:
            inst = instances.get(uuid)
            name = "" if inst is None else inst.name
        return cls(
            uuid=uuid,
            name=name,
            type_name=owner.name,
            input_type=input_type,
            output_type=output_type,
            nodes=[
                FunctionNodeView(
                    uuid=node.uuid,
                    kind=node.kind,
                    position=node.position,
                    config=node.config,
                )
                for node in WFunction.nodes(uuid)
            ],
            edges=[
                FunctionEdgeView(
                    uuid=edge.uuid,
                    from_node_uuid=edge.from_node_uuid,
                    from_port=edge.from_port,
                    to_node_uuid=edge.to_node_uuid,
                    to_port=edge.to_port,
                )
                for edge in WFunction.edges(uuid)
            ],
        )
