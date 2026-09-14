"""Statement helpers for a function's action DAG (ADR-0007/0019).

Nodes + edges are persisted together (``sync_graph`` replaces the whole
DAG), so both tables' statements live in this one module — the
``function_nodes`` / ``function_edges`` modules keep only the TABLE
definitions.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes


@databasemethod(commit=False)
def nodes_of(function_uuid: UUID) -> list[TABLE_FunctionNodes]:
    """The function's DAG nodes, in layout order."""
    return list(
        Database.session.scalars(
            sqla.select(TABLE_FunctionNodes)
            .where(TABLE_FunctionNodes.function_uuid == function_uuid)
            .order_by(TABLE_FunctionNodes.position)
        ).all()
    )


@databasemethod(commit=False)
def edges_of(function_uuid: UUID) -> list[TABLE_FunctionEdges]:
    """The function's dataflow edges."""
    return list(
        Database.session.scalars(
            sqla.select(TABLE_FunctionEdges).where(
                TABLE_FunctionEdges.function_uuid == function_uuid
            )
        ).all()
    )


@databasemethod(commit=False)
def sync_graph(
    function_uuid: UUID,
    nodes: Sequence[tuple[UUID | None, str, int, Mapping[str, object]]],
    edges: Sequence[tuple[UUID, int, UUID, int]],
) -> None:
    """Replace the function's DAG. `nodes` items are
    (uuid | None, kind, position, config); None uuid creates. `edges`
    items are (from_node_uuid, from_port, to_node_uuid, to_port) — edges
    are non-identity (no client uuids), so they are dropped and rebuilt."""
    existing_nodes = nodes_of(function_uuid)
    existing_uuids = {n.uuid for n in existing_nodes}
    kept: set[UUID] = set()
    for node_uuid, kind, position, config in nodes:
        if node_uuid is not None and node_uuid in existing_uuids:
            row = Database.session.get(TABLE_FunctionNodes, node_uuid)
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
            Database.session.add(row)
            kept.add(row.uuid)
    for stale in existing_nodes:
        if stale.uuid not in kept:
            Database.session.delete(stale)
    Database.session.flush()
    _ = Database.session.execute(
        sqla.delete(TABLE_FunctionEdges).where(
            TABLE_FunctionEdges.function_uuid == function_uuid
        )
    )
    for from_uuid, from_port, to_uuid, to_port in edges:
        Database.session.add(
            TABLE_FunctionEdges(
                function_uuid=function_uuid,
                from_node_uuid=from_uuid,
                from_port=from_port,
                to_node_uuid=to_uuid,
                to_port=to_port,
            )
        )
    Database.session.flush()
