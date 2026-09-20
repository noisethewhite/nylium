"""Function nodes store — DAG node reads and whole-DAG sync (ADR-0031).

Nodes + edges are persisted together (``sync_graph`` replaces the whole
DAG), so ``sync_graph`` lives here alongside ``nodes_of``; the
``function_nodes`` / ``function_edges`` table modules keep only the
``TABLE_*`` definitions. Moved from ``objects/wfunction/graph.py``
(ADR-0030 phase C).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.rows.functions.function_node import FunctionNode
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes


class FunctionNodes(Table[UUID, FunctionNode]):
    """The function_nodes table as a store of DAG nodes (and DAG sync)."""

    __row__: ClassVar[type[Row]] = FunctionNode

    @classmethod
    @Database.use_same_session
    def nodes_of(cls, function_uuid: UUID) -> list[TABLE_FunctionNodes]:
        """The function's DAG nodes, in layout order."""
        return list(
            Database.scalars(
                sqla.select(TABLE_FunctionNodes)
                .where(TABLE_FunctionNodes.function_uuid == function_uuid)
                .order_by(TABLE_FunctionNodes.position)
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
        """Replace the function's DAG. `nodes` items are
        (uuid | None, kind, position, config); None uuid creates. `edges`
        items are (from_node_uuid, from_port, to_node_uuid, to_port) — edges
        are non-identity (no client uuids), so they are dropped and rebuilt."""
        existing_nodes = cls.nodes_of(function_uuid)
        existing_uuids = {n.uuid for n in existing_nodes}
        kept: set[UUID] = set()
        for node_uuid, kind, position, config in nodes:
            if node_uuid is not None and node_uuid in existing_uuids:
                row = Database.get(TABLE_FunctionNodes, node_uuid)
                if row is not None:
                    row.kind = kind
                    row.position = position
                    row.config = dict(config)
                    kept.add(node_uuid)
            else:
                row = TABLE_FunctionNodes(
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
        _ = Database.execute(
            sqla.delete(TABLE_FunctionEdges).where(
                TABLE_FunctionEdges.function_uuid == function_uuid
            )
        )
        for from_uuid, from_port, to_uuid, to_port in edges:
            Database.add(
                TABLE_FunctionEdges(
                    function_uuid=function_uuid,
                    from_node_uuid=from_uuid,
                    from_port=from_port,
                    to_node_uuid=to_uuid,
                    to_port=to_port,
                )
            )
        Database.flush()


function_nodes = FunctionNodes()
