from __future__ import annotations
from nylium.database import Database
from nylium.objects.nyfunction.FunctionEdgeView import FunctionEdgeView
from nylium.objects.nyfunction.FunctionNodeView import FunctionNodeView
from nylium.Constants import Constants
from nylium.objects.nyfunction.NyFunction import NyFunction
from nylium.objects.nyobject.NyObject import NyObject
from nylium.objects.NyType import NyType
from typing import Self
from uuid import UUID
from typing import cast
from pydantic.dataclasses import dataclass
from nylium.data.tables import instances
from nylium.uuid import FunctionUUID, ObjectUUID, TypeUUID


@dataclass(config=Constants.Pydantic.CONFIG)
class FunctionView:
    """Snapshot of one Function<T,R> instance: its parameterization and its
    full action DAG (nodes + edges). ADR-0029: no input link — the input is
    the sibling props of the object the function is bound into."""

    uuid: ObjectUUID
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
        owner = NyType.by_uuid(TypeUUID.of(type_uuid))
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
            uuid=ObjectUUID.of(uuid),
            name=name,
            type_name=owner.name,
            input_type=input_type,
            output_type=output_type,
            nodes=[
                FunctionNodeView(
                    uuid=FunctionUUID.of(node.uuid),
                    kind=node.kind,
                    position=node.position,
                    config=node.config,
                )
                for node in NyFunction.nodes(ObjectUUID.of(uuid))
            ],
            edges=[
                FunctionEdgeView(
                    uuid=FunctionUUID.of(edge.uuid),
                    from_node_uuid=FunctionUUID.of(edge.from_node_uuid),
                    from_port=edge.from_port,
                    to_node_uuid=FunctionUUID.of(edge.to_node_uuid),
                    to_port=edge.to_port,
                )
                for edge in NyFunction.edges(ObjectUUID.of(uuid))
            ],
        )
