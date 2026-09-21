"""The function_nodes table: FunctionNode (mapped Row) + FunctionNodes (store)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class FunctionNode(Row):
    __tablename__: ClassVar[str] = "function_nodes"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    config: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default_factory=dict
    )


class FunctionNodes(Table[UUID, FunctionNode]):
    """The function_nodes table as a store of DAG nodes (and DAG sync)."""

    __row__: ClassVar[type[Row]] = FunctionNode

    @classmethod
    @Database.use_same_session
    def nodes_of(cls, function_uuid: UUID) -> list[FunctionNode]:
        c = mapper(FunctionNode).columns
        return list(
            Database.scalars(
                sqla.select(FunctionNode)
                .where(c.function_uuid == function_uuid)
                .order_by(c.position)
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def sync_graph(
        cls,
        function_uuid: UUID,
        nodes: Sequence[tuple[UUID | None, str, int, Mapping[str, object]]],
        edges: Sequence[tuple[UUID, int, UUID, int]],
    ) -> None:
        from nylium.table_rows.functions.function_edge import FunctionEdge

        existing_nodes = cls.nodes_of(function_uuid)
        existing_uuids = {n.uuid for n in existing_nodes}
        kept: set[UUID] = set()
        for node_uuid, kind, position, config in nodes:
            if node_uuid is not None and node_uuid in existing_uuids:
                row = Database.get(FunctionNode, node_uuid)
                if row is not None:
                    row.kind = kind
                    row.position = position
                    row.config = dict(config)
                    kept.add(node_uuid)
            else:
                row = FunctionNode(
                    uuid=node_uuid or uuid4(),
                    function_uuid=function_uuid,
                    kind=kind,
                    position=position,
                    config=dict(config),
                )
                Database.add(row)
                kept.add(row.uuid)
        for stale in existing_nodes:
            if stale.uuid not in kept:
                Database.delete(stale)
        Database.flush()
        fe_c = mapper(FunctionEdge).columns
        _ = Database.execute(
            sqla.delete(FunctionEdge).where(fe_c.function_uuid == function_uuid)
        )
        for from_uuid, from_port, to_uuid, to_port in edges:
            Database.add(
                FunctionEdge(
                    function_uuid=function_uuid,
                    from_node_uuid=from_uuid,
                    from_port=from_port,
                    to_node_uuid=to_uuid,
                    to_port=to_port,
                )
            )
        Database.flush()


function_nodes = FunctionNodes()
