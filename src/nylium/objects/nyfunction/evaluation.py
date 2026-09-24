"""NyFunction interpreter (ADR-0007): folds the DAG over a materialized
input mapping. Each node kind is a closed, hand-written operation — no
``eval``, no third-party deps, so the arbitrary-code surface is
structurally shut."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import cast
from uuid import UUID

from nylium.database import Database
from nylium.data.rows import FunctionEdge
from nylium.data.tables import FunctionEdges
from nylium.data.tables import FunctionNodes
from nylium.objects.NyInteger import NyInteger
from nylium.objects.NyString import NyString
from nylium.objects.NyScalar import ScalarPayload
from nylium.objects.nyfunction.constants import fail
from nylium.objects.nyfunction.validation import topo_sort
from nylium.Constants import Constants


@Database.use_same_session
def evaluate(
    function_uuid: UUID, input_values: Mapping[str, object]
) -> ScalarPayload | None:
    """Fold the function's DAG over a materialized input object (a plain
    prop-key -> value mapping). Returns the sink's value, or None on a
    div-by-zero / missing input. No DB reads of the input — the caller
    hands the data in."""
    nodes = FunctionNodes.nodes_of(function_uuid)
    edges = FunctionEdges.edges_of(function_uuid)
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


def _is_sink(node_uuid: UUID, edges: Iterable[FunctionEdge]) -> bool:
    return all(edge.from_node_uuid != node_uuid for edge in edges)


def _eval_node(
    kind: str,
    config: Mapping[str, object],
    inputs: list[object],
    input_values: Mapping[str, object],
) -> object:
    if kind == Constants.Functions.NODE_GET_PROP:
        key = cast(str, config["key"])
        return input_values.get(key)
    if kind == Constants.Functions.NODE_CONST:
        value = config["value"]
        if isinstance(value, float):
            return Decimal(str(value))
        return value
    if kind in (Constants.Functions.NODE_ADD, Constants.Functions.NODE_SUB, Constants.Functions.NODE_MUL, Constants.Functions.NODE_DIV):
        left = _as_decimal(inputs[0])
        right = _as_decimal(inputs[1])
        if left is None or right is None:
            raise InvalidOperation
        if kind == Constants.Functions.NODE_ADD:
            return left + right
        if kind == Constants.Functions.NODE_SUB:
            return left - right
        if kind == Constants.Functions.NODE_MUL:
            return left * right
        return left / right
    if kind == Constants.Functions.NODE_COUNT:
        seq = inputs[0]
        if seq is None:
            return 0
        return len(cast(list[object], seq))
    if kind in (Constants.Functions.NODE_SUM, Constants.Functions.NODE_AVERAGE, Constants.Functions.NODE_MIN, Constants.Functions.NODE_MAX):
        seq = inputs[0]
        if seq is None:
            return None
        values = [_as_decimal(v) for v in cast(list[object], seq)]
        if any(v is None for v in values):
            raise InvalidOperation
        decimals: list[Decimal] = [v for v in values if v is not None]
        if not decimals:
            return Decimal(0)
        if kind == Constants.Functions.NODE_SUM:
            return sum(decimals, Decimal(0))
        if kind == Constants.Functions.NODE_AVERAGE:
            return sum(decimals, Decimal(0)) / Decimal(len(decimals))
        if kind == Constants.Functions.NODE_MIN:
            return min(decimals)
        return max(decimals)
    if kind == Constants.Functions.NODE_CAST:
        target = cast(str, config["target"])
        src = inputs[0]
        if target == NyString.TYPE_NAME:
            return "" if src is None else str(src)
        if src is None:
            return None
        if target == NyInteger.TYPE_NAME:
            return int(Decimal(str(src)))
        return Decimal(str(src))
    if kind == Constants.Functions.NODE_MAP:
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
