"""NyFunction graph validation (ADR-0007): internal acyclicity (topo
sort), port arity, edge referential integrity, node type conformance and
the single-sink output check. Runs on a draft DAG before any row
persists."""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from nylium.database import Database
from nylium.ny.nyfunction.constants import NodeType, fail
from nylium.ny.nyfunction.typing import (
    NODE_ARITY,
    check_inputs,
    node_output_type,
)


@Database.use_same_session
def validate_graph(
    nodes: list[tuple[UUID, str, Mapping[str, object]]],
    edges: list[tuple[UUID, int, UUID, int]],
    input_type: str,
    output_type: str,
) -> None:
    """Validate a full DAG draft (before any row persists). Checks:
    internal acyclicity (topo sort), port arity, edge referential
    integrity, node type conformance, and that the single sink node's
    output type equals `output_type`."""
    node_uuids = {uuid for uuid, _, _ in nodes}
    if len(node_uuids) != len(nodes):
        fail("duplicate node uuid in graph")
    kinds: dict[UUID, str] = {u: k for u, k, _ in nodes}
    configs: dict[UUID, Mapping[str, object]] = {u: c for u, _, c in nodes}

    # referential integrity + port arity
    arity: dict[UUID, int] = {}
    for node_uuid, kind, _ in nodes:
        if kind not in NODE_ARITY:
            fail(f"unknown node kind {kind!r}")
        arity[node_uuid] = NODE_ARITY[kind]
    incoming: dict[UUID, list[tuple[UUID, int]]] = {u: [] for u in node_uuids}
    outgoing: dict[UUID, int] = {u: 0 for u in node_uuids}
    for from_uuid, from_port, to_uuid, to_port in edges:
        if from_uuid not in node_uuids:
            fail(f"edge references unknown from-node {from_uuid}")
        if to_uuid not in node_uuids:
            fail(f"edge references unknown to-node {to_uuid}")
        if from_port != 0:
            fail("nodes have a single output; from_port must be 0")
        if to_port < 0 or to_port >= arity[to_uuid]:
            fail(
                f"to_port {to_port} out of range for {kinds[to_uuid]} (arity {arity[to_uuid]})"
            )
        incoming[to_uuid].append((from_uuid, to_port))
        outgoing[from_uuid] += 1

    # arity: a node must receive exactly its declared number of inputs
    for node_uuid, expected in arity.items():
        got = len(incoming[node_uuid])
        if got != expected:
            fail(
                f"node {kinds[node_uuid]} expects {expected} inputs, got {got}"
            )

    # topological sort — a back-edge is an internal cycle
    order = topo_sort(node_uuids, incoming)
    if order is None:
        fail("function graph contains a cycle")

    # single sink (no outgoing edges) — it is the function output
    sinks = [u for u, n in outgoing.items() if n == 0]
    if len(sinks) != 1:
        fail(f"function graph must have exactly one output node, found {len(sinks)}")

    # type conformance, in topo order (inputs resolved before use)
    node_types: dict[UUID, NodeType] = {}
    for node_uuid in order:
        in_uuids = [src for src, _ in sorted(incoming[node_uuid], key=lambda e: e[1])]
        input_types = [node_types[src] for src in in_uuids]
        kind = kinds[node_uuid]
        check_inputs(kind, input_types)
        node_types[node_uuid] = node_output_type(
            kind, configs[node_uuid], input_type, input_types
        )

    sink_type = node_types[sinks[0]]
    if sink_type != output_type:
        fail(
            f"function output is {sink_type!r}, but the type declares {output_type!r}"
        )


def topo_sort(
    node_uuids: set[UUID],
    incoming: dict[UUID, list[tuple[UUID, int]]],
) -> list[UUID] | None:
    """Kahn's algorithm; returns None on a cycle."""
    indegree = {u: len(incoming[u]) for u in node_uuids}
    dependents: dict[UUID, list[UUID]] = {u: [] for u in node_uuids}
    for node_uuid, sources in incoming.items():
        for src, _ in sources:
            dependents[src].append(node_uuid)
    queue = [u for u in node_uuids if indegree[u] == 0]
    order: list[UUID] = []
    while queue:
        node_uuid = queue.pop(0)
        order.append(node_uuid)
        for dep in dependents[node_uuid]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)
    if len(order) != len(node_uuids):
        return None
    return order
