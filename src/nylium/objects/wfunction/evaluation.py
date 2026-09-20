"""WFunction interpreter (ADR-0007): folds the DAG over a materialized
input mapping. Each node kind is a closed, hand-written operation — no
``eval``, no third-party deps, so the arbitrary-code surface is
structurally shut."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import cast
from uuid import UUID

from nylium.database import use_same_session
from nylium.tables.functions import graph
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.objects.wscalar import ScalarPayload, WInteger, WString
from nylium.objects.wfunction.constants import (
    NODE_ADD,
    NODE_AVERAGE,
    NODE_CAST,
    NODE_CONST,
    NODE_COUNT,
    NODE_DIV,
    NODE_GET_PROP,
    NODE_MAP,
    NODE_MAX,
    NODE_MIN,
    NODE_MUL,
    NODE_SUB,
    NODE_SUM,
    fail,
)
from nylium.objects.wfunction.validation import topo_sort


@use_same_session
def evaluate(
    function_uuid: UUID, input_values: Mapping[str, object]
) -> ScalarPayload | None:
    """Fold the function's DAG over a materialized input object (a plain
    prop-key -> value mapping). Returns the sink's value, or None on a
    div-by-zero / missing input. No DB reads of the input — the caller
    hands the data in."""
    nodes = graph.nodes_of(function_uuid)
    edges = graph.edges_of(function_uuid)
    node_uuids = {u.uuid for u in nodes}
    kinds = {u.uuid: u.kind for u in nodes}
    configs = {u.uuid: cast(Mapping[str, object], u.config) for u in nodes}
    incoming: dict[UUID, list[tuple[UUID, int]]] = {u.uuid: [] for u in nodes}
    for edge in edges:
        incoming[edge.to_node_uuid].append((edge.from_node_uuid, edge.to_port))
    order = topo_sort(node_uuids, incoming)
    if order is None:
        raise RuntimeError("function graph cycle reached evaluate (should be validated)")

    values: dict[UUID, object] = {}
    try:
        for node_uuid in order:
            kind = kinds[node_uuid]
            config = configs[node_uuid]
            in_uuids = [src for src, _ in sorted(incoming[node_uuid], key=lambda e: e[1])]
            inputs = [values[s] for s in in_uuids]
            values[node_uuid] = _eval_node(
                kind, config, inputs, input_values
            )
    except (ZeroDivisionError, InvalidOperation):
        return None
    sink = next(
        u for u in node_uuids if _is_sink(u, edges)
    )
    return cast(ScalarPayload | None, values[sink])


def _is_sink(node_uuid: UUID, edges: Iterable[TABLE_FunctionEdges]) -> bool:
    return all(edge.from_node_uuid != node_uuid for edge in edges)


def _eval_node(
    kind: str,
    config: Mapping[str, object],
    inputs: list[object],
    input_values: Mapping[str, object],
) -> object:
    if kind == NODE_GET_PROP:
        key = cast(str, config["key"])
        return input_values.get(key)
    if kind == NODE_CONST:
        value = config["value"]
        if isinstance(value, float):
            return Decimal(str(value))
        return value
    if kind in (NODE_ADD, NODE_SUB, NODE_MUL, NODE_DIV):
        left = _as_decimal(inputs[0])
        right = _as_decimal(inputs[1])
        if left is None or right is None:
            raise InvalidOperation
        if kind == NODE_ADD:
            return left + right
        if kind == NODE_SUB:
            return left - right
        if kind == NODE_MUL:
            return left * right
        return left / right
    if kind == NODE_COUNT:
        seq = inputs[0]
        if seq is None:
            return 0
        return len(cast(list[object], seq))
    if kind in (NODE_SUM, NODE_AVERAGE, NODE_MIN, NODE_MAX):
        seq = inputs[0]
        if seq is None:
            return None
        values = [_as_decimal(v) for v in cast(list[object], seq)]
        if any(v is None for v in values):
            raise InvalidOperation
        decimals: list[Decimal] = [v for v in values if v is not None]
        if not decimals:
            return Decimal(0)
        if kind == NODE_SUM:
            return sum(decimals, Decimal(0))
        if kind == NODE_AVERAGE:
            return sum(decimals, Decimal(0)) / Decimal(len(decimals))
        if kind == NODE_MIN:
            return min(decimals)
        return max(decimals)
    if kind == NODE_CAST:
        target = cast(str, config["target"])
        src = inputs[0]
        if target == WString.TYPE_NAME:
            return "" if src is None else str(src)
        if src is None:
            return None
        if target == WInteger.TYPE_NAME:
            return int(Decimal(str(src)))
        return Decimal(str(src))
    if kind == NODE_MAP:
        key = cast(str, config["key"])
        seq = inputs[0]
        if seq is None:
            return []
        return [_read_prop(elem, key) for elem in cast(list[object], seq)]
    fail(f"unknown node kind {kind!r}")


def _as_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return None


def _read_prop(elem: object, key: str) -> object:
    """Read one prop off an array element (an object wrapper)."""
    if elem is None:
        return None
    return cast(object, getattr(elem, key))
