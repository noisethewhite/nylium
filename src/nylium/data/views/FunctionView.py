from __future__ import annotations
from nylium.database import Database
from nylium.data.views.FunctionEdgeView import FunctionEdgeView
from nylium.data.views.FunctionNodeView import FunctionNodeView
from nylium.Constants import Constants
from nylium.ny.nyfunction import NyFunction
from nylium.ny.nyobject import NyObject
from nylium.ny import NyType
from typing import Self
from uuid import UUID
from typing import cast
from pydantic.dataclasses import dataclass
from nylium.data.tables import instances
from nylium.uuid import FunctionRef, ObjectRef, TypeRef


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionView:
    """Snapshot of one Function<T,R> instance: its parameterization and its
    full action DAG (nodes + edges). ADR-0029: no input link — the input is
    the sibling props of the object the function is bound into."""

    uuid: ObjectRef
    name: str
    type_name: str
    input_type: str
    output_type: str
    nodes: list[FunctionNodeView]
    edges: list[FunctionEdgeView]

    @classmethod
    @Database.use_same_session
    def from_uuid(cls, uuid: UUID) -> Self | None:
        inst = instances.get(uuid)
        type_uuid = None if inst is None else inst.type_uuid
        if type_uuid is None:
            return None
        owner = NyType.by_uuid(TypeRef.of(type_uuid))
        if owner is None or not owner.is_function:
            return None
        params = NyType.function_params(owner.name)
        if params is None:
            return None
        input_type, output_type = params
        wrapper = NyObject.wrap(uuid)
        name = cast(str | None, getattr(wrapper, Constants.Props.NAME_PROP_KEY))
        if not name:
            inst = instances.get(uuid)
            name = "" if inst is None else inst.name
        return cls(
            uuid=ObjectRef.of(uuid),
            name=name,
            type_name=owner.name,
            input_type=input_type,
            output_type=output_type,
            nodes=[
                FunctionNodeView(
                    uuid=FunctionRef.of(node.uuid),
                    kind=node.kind,
                    position=node.position,
                    config=node.config,
                )
                for node in NyFunction.nodes(ObjectRef.of(uuid))
            ],
            edges=[
                FunctionEdgeView(
                    uuid=FunctionRef.of(edge.uuid),
                    from_node_uuid=FunctionRef.of(edge.from_node_uuid),
                    from_port=edge.from_port,
                    to_node_uuid=FunctionRef.of(edge.to_node_uuid),
                    to_port=edge.to_port,
                )
                for edge in NyFunction.edges(ObjectRef.of(uuid))
            ],
        )
