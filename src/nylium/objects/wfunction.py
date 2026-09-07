"""WFunction: the Function<T, R> type kind (ADR-0007).

A function type is parameterized on an input object type ``T`` and a
scalar output ``R`` (``Function<Invoice, Numeric>``). A function
*instance* carries one pinned prop ``input`` (a link to a ``T`` object)
and a body — an action DAG stored in ``function_nodes`` / ``function_edges``
keyed by the instance uuid.

This module owns, end to end: the node whitelist, static validation of
the DAG (topological sort for internal cycles, port arity, type
conformance, sink type == R), the pure interpreter that folds the DAG
over a materialized input object, and the recompute dependency index
(``function_deps``).

No ``eval``, no third-party deps — each node kind is a closed, hand
written operation, so the arbitrary-code surface is structurally shut.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import ClassVar, NoReturn, TypeAlias, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.tables import (
    TABLE_FunctionDeps,
    TABLE_FunctionEdges,
    TABLE_FunctionNodes,
    TABLE_InstanceValues,
    TABLE_Instances,
    instances,
)
from nylium.tables.types import TABLE_Types
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WInteger, WNumeric, WString, WScalar
from nylium.objects.wtype import WType

# The closed set of node operations. The `kind` string is validated
# against this set at save time.
NODE_GET_PROP = "get_prop"
NODE_CONST = "const"
NODE_ADD = "add"
NODE_SUB = "sub"
NODE_MUL = "mul"
NODE_DIV = "div"
NODE_SUM = "sum"
NODE_AVERAGE = "average"
NODE_COUNT = "count"
NODE_MIN = "min"
NODE_MAX = "max"
NODE_CAST = "cast"
NODE_MAP = "map"

# The one pinned prop a function type carries: a link to its input object.
INPUT_PROP_KEY = "input"

# The object title prop (mirrors api.NAME_PROP_KEY) — pinned first on every
# object type, including function types.
NAME_PROP_KEY = "name"

# A node output type: an exact scalar TYPE_NAME, or an Array<ElementTypeName>.
NodeType: TypeAlias = str

_NUMERIC_SCALARS = frozenset({WInteger.TYPE_NAME, WNumeric.TYPE_NAME})


def _error(message: str) -> NoReturn:
    from nylium.server.errors import ValidationError

    raise ValidationError(message)


def _is_numeric_scalar(name: str) -> bool:
    return name in _NUMERIC_SCALARS


def _is_array_type(name: str) -> bool:
    return WType.is_array_name(name)


class WFunction:
    """Function type / graph surface (ADR-0007)."""

    # kind -> (input arity, output type, config validator)
    NODES: ClassVar[dict[str, int]] = {
        NODE_GET_PROP: 0,
        NODE_CONST: 0,
        NODE_ADD: 2,
        NODE_SUB: 2,
        NODE_MUL: 2,
        NODE_DIV: 2,
        NODE_SUM: 1,
        NODE_AVERAGE: 1,
        NODE_COUNT: 1,
        NODE_MIN: 1,
        NODE_MAX: 1,
        NODE_CAST: 1,
        NODE_MAP: 1,
    }

    @classmethod
    def is_function(cls, type_name: str) -> bool:
        owner = WType.by_name(type_name)
        return owner is not None and owner.is_function

    # --- type creation ---

    @classmethod
    @databasemethod(commit=True)
    def ensure_type(cls, input_name: str, output_name: str) -> WType:
        """Materialize (or fetch) the parameterized Function<T, R> type and
        its pinned props: `name` (String, like every object type) and
        `input` (a link to a T object). `output_name` must name a scalar."""
        from nylium.server.errors import ValidationError

        if WScalar.by_type_name(output_name) is None:
            raise ValidationError(
                f"function output must be a scalar type, got {output_name!r}"
            )
        input_type = WType.by_name(input_name)
        if input_type is None:
            raise ValidationError(f"no type {input_name!r} for the function input")
        if input_type.is_embedded:
            raise ValidationError(
                f"function input {input_name!r} is embedded — link a standalone object"
            )
        type_name = WType.function_name(input_name, output_name)
        owner = WType.ensure(type_name, kind=WType.KIND_FUNCTION)
        # `name` (String) is pinned first, like every object type; `input`
        # (a link to T) second.
        name_type = WType.by_name(WString.TYPE_NAME)
        if name_type is None:
            name_type = WType.ensure(WString.TYPE_NAME)
        _ = WProp.ensure(owner, NAME_PROP_KEY, name_type, position=0)
        _ = WProp.ensure(owner, INPUT_PROP_KEY, input_type, position=1)
        return owner

    # --- node config ---

    @classmethod
    def node_output_type(
        cls,
        kind: str,
        config: Mapping[str, object],
        input_type: str,
        input_types: list[NodeType],
    ) -> NodeType:
        """The static output type of a node, given the function's input
        type `T` (for `get_prop` lookups) and the node's config."""
        if kind == NODE_GET_PROP:
            key = config.get("key")
            if not isinstance(key, str):
                _error("get_prop needs a string 'key' in config")
            owner = WType.by_name(input_type)
            if owner is None:
                _error(f"cannot resolve function input type {input_type!r}")
            prop = WProp.by_key(owner, key)
            if prop is None:
                _error(f"get_prop references unknown prop {key!r} of {input_type}")
            value_name = prop.value_type().name
            if WScalar.by_type_name(value_name) is not None:
                return value_name
            if _is_array_type(value_name):
                return value_name
            _error(
                f"get_prop can only read scalar or array props, got {value_name!r}"
            )
        if kind == NODE_MAP:
            key = config.get("key")
            if not isinstance(key, str):
                _error("map needs a string 'key' in config")
            array_type = input_types[0]
            if not _is_array_type(array_type):
                _error(f"map needs an array input, got {array_type!r}")
            element = WType.element_name(array_type)
            owner = WType.by_name(element)
            if owner is None:
                _error(f"cannot resolve map element type {element!r}")
            prop = WProp.by_key(owner, key)
            if prop is None:
                _error(f"map references unknown prop {key!r} of {element}")
            value_name = prop.value_type().name
            if WScalar.by_type_name(value_name) is None and not _is_array_type(value_name):
                _error(f"map can only read scalar or array props, got {value_name!r}")
            return WType.array_name(value_name)
        if kind == NODE_CONST:
            value = config.get("value")
            if isinstance(value, bool) or value is None:
                _error("const needs a number or string 'value'")
            if isinstance(value, int):
                return WInteger.TYPE_NAME
            if isinstance(value, (float, str)):
                return WNumeric.TYPE_NAME if isinstance(value, float) else WString.TYPE_NAME
            _error("const value must be an int, float or str")
        if kind in (NODE_ADD, NODE_SUB, NODE_MUL, NODE_DIV):
            return WNumeric.TYPE_NAME
        if kind in (NODE_SUM, NODE_AVERAGE, NODE_MIN, NODE_MAX):
            return WNumeric.TYPE_NAME
        if kind == NODE_COUNT:
            return WInteger.TYPE_NAME
        if kind == NODE_CAST:
            target = config.get("target")
            if not isinstance(target, str) or WScalar.by_type_name(target) is None:
                _error("cast needs a scalar 'target' in config")
            return target
        _error(f"unknown node kind {kind!r}")

    @classmethod
    def _check_inputs(cls, kind: str, input_types: list[NodeType]) -> None:
        """Type-conformance check on a node's resolved input types."""
        if kind in (NODE_ADD, NODE_SUB, NODE_MUL, NODE_DIV):
            for t in input_types:
                if not _is_numeric_scalar(t):
                    _error(f"{kind} needs numeric inputs, got {t!r}")
            return
        if kind in (NODE_SUM, NODE_AVERAGE, NODE_MIN, NODE_MAX):
            array_type = input_types[0]
            if not _is_array_type(array_type):
                _error(f"{kind} needs an array input, got {array_type!r}")
            element = WType.element_name(array_type)
            if not _is_numeric_scalar(element):
                _error(f"{kind} needs a numeric array, got Array<{element}>")
            return
        if kind == NODE_COUNT:
            if not _is_array_type(input_types[0]):
                _error(f"count needs an array input, got {input_types[0]!r}")
            return
        if kind == NODE_CAST:
            src = input_types[0]
            if src not in _NUMERIC_SCALARS and src != WString.TYPE_NAME:
                _error(f"cast needs a numeric or string input, got {src!r}")
        if kind == NODE_MAP:
            array_type = input_types[0]
            if not _is_array_type(array_type):
                _error(f"map needs an array input, got {array_type!r}")
            element = WType.element_name(array_type)
            if WScalar.by_type_name(element) is not None or WType.is_array_name(element):
                _error(f"map needs an array of objects, got Array<{element}>")

    # --- graph validation ---

    @classmethod
    @databasemethod(commit=False)
    def validate_graph(
        cls,
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
            _error("duplicate node uuid in graph")
        kinds: dict[UUID, str] = {u: k for u, k, _ in nodes}
        configs: dict[UUID, Mapping[str, object]] = {u: c for u, _, c in nodes}

        # referential integrity + port arity
        arity: dict[UUID, int] = {}
        for node_uuid, kind, _ in nodes:
            if kind not in cls.NODES:
                _error(f"unknown node kind {kind!r}")
            arity[node_uuid] = cls.NODES[kind]
        incoming: dict[UUID, list[tuple[UUID, int]]] = {u: [] for u in node_uuids}
        outgoing: dict[UUID, int] = {u: 0 for u in node_uuids}
        for from_uuid, from_port, to_uuid, to_port in edges:
            if from_uuid not in node_uuids:
                _error(f"edge references unknown from-node {from_uuid}")
            if to_uuid not in node_uuids:
                _error(f"edge references unknown to-node {to_uuid}")
            if from_port != 0:
                _error("nodes have a single output; from_port must be 0")
            if to_port < 0 or to_port >= arity[to_uuid]:
                _error(
                    f"to_port {to_port} out of range for {kinds[to_uuid]} (arity {arity[to_uuid]})"
                )
            incoming[to_uuid].append((from_uuid, to_port))
            outgoing[from_uuid] += 1

        # arity: a node must receive exactly its declared number of inputs
        for node_uuid, expected in arity.items():
            got = len(incoming[node_uuid])
            if got != expected:
                _error(
                    f"node {kinds[node_uuid]} expects {expected} inputs, got {got}"
                )

        # topological sort — a back-edge is an internal cycle
        order = cls._topo_sort(node_uuids, incoming)
        if order is None:
            _error("function graph contains a cycle")

        # single sink (no outgoing edges) — it is the function output
        sinks = [u for u, n in outgoing.items() if n == 0]
        if len(sinks) != 1:
            _error(f"function graph must have exactly one output node, found {len(sinks)}")

        # type conformance, in topo order (inputs resolved before use)
        node_types: dict[UUID, NodeType] = {}
        for node_uuid in order:
            in_uuids = [src for src, _ in sorted(incoming[node_uuid], key=lambda e: e[1])]
            input_types = [node_types[src] for src in in_uuids]
            kind = kinds[node_uuid]
            cls._check_inputs(kind, input_types)
            node_types[node_uuid] = cls.node_output_type(
                kind, configs[node_uuid], input_type, input_types
            )

        sink_type = node_types[sinks[0]]
        if sink_type != output_type:
            _error(
                f"function output is {sink_type!r}, but the type declares {output_type!r}"
            )

    @classmethod
    def _topo_sort(
        cls,
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

    # --- evaluation ---

    @classmethod
    @databasemethod(commit=False)
    def evaluate(
        cls, function_uuid: UUID, input_values: Mapping[str, object]
    ) -> ScalarPayload | None:
        """Fold the function's DAG over a materialized input object (a plain
        prop-key -> value mapping). Returns the sink's value, or None on a
        div-by-zero / missing input. No DB reads of the input — the caller
        hands the data in."""
        nodes = cls._nodes(function_uuid)
        edges = cls._edges(function_uuid)
        node_uuids = {u.uuid for u in nodes}
        kinds = {u.uuid: u.kind for u in nodes}
        configs = {u.uuid: cast(Mapping[str, object], u.config) for u in nodes}
        incoming: dict[UUID, list[tuple[UUID, int]]] = {u.uuid: [] for u in nodes}
        for edge in edges:
            incoming[edge.to_node_uuid].append((edge.from_node_uuid, edge.to_port))
        order = cls._topo_sort(node_uuids, incoming)
        if order is None:
            raise RuntimeError("function graph cycle reached evaluate (should be validated)")

        values: dict[UUID, object] = {}
        try:
            for node_uuid in order:
                kind = kinds[node_uuid]
                config = configs[node_uuid]
                in_uuids = [src for src, _ in sorted(incoming[node_uuid], key=lambda e: e[1])]
                inputs = [values[s] for s in in_uuids]
                values[node_uuid] = cls._eval_node(
                    kind, config, inputs, input_values
                )
        except (ZeroDivisionError, InvalidOperation):
            return None
        sink = next(
            u for u in node_uuids if cls._is_sink(u, edges)
        )
        return cast(ScalarPayload | None, values[sink])

    @classmethod
    def _is_sink(cls, node_uuid: UUID, edges: Iterable[TABLE_FunctionEdges]) -> bool:
        return all(edge.from_node_uuid != node_uuid for edge in edges)

    @classmethod
    def _eval_node(
        cls,
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
            left = cls._as_decimal(inputs[0])
            right = cls._as_decimal(inputs[1])
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
            values = [cls._as_decimal(v) for v in cast(list[object], seq)]
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
            return [cls._read_prop(elem, key) for elem in cast(list[object], seq)]
        _error(f"unknown node kind {kind!r}")

    @classmethod
    def _as_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, Decimal)):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        return None

    @classmethod
    def _read_prop(cls, elem: object, key: str) -> object:
        """Read one prop off an array element (an object wrapper)."""
        if elem is None:
            return None
        return cast(object, getattr(elem, key))

    # --- input materialization ---

    @classmethod
    @databasemethod(commit=False)
    def input_object_uuid(
        cls, function_uuid: UUID
    ) -> UUID | None:
        """The object the function currently reads as its input (its pinned
        `input` link), or None when the link is unset."""
        inst = Database.session.get(TABLE_Instances, function_uuid)
        if inst is None:
            return None
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None or not owner.is_function:
            return None
        prop = WProp.by_key(owner, INPUT_PROP_KEY)
        if prop is None:
            return None
        return Database.session.scalar(
            sqla.select(TABLE_InstanceValues.uuid).where(
                TABLE_InstanceValues.inst_uuid == function_uuid,
                TABLE_InstanceValues.prop_uuid == prop.uuid,
            )
        )

    @classmethod
    @databasemethod(commit=False)
    def materialize_input(cls, function_uuid: UUID) -> dict[str, object]:
        """Project the function's input object to a prop-key -> value mapping
        the interpreter can fold over. A prop that is itself function-backed
        is resolved recursively (composition: a function can read another
        function's output). No input link -> empty mapping."""
        from nylium.objects.wobject import WObject

        input_uuid = cls.input_object_uuid(function_uuid)
        if input_uuid is None:
            return {}
        wrapper = WObject.wrap(input_uuid)
        inst = instances.get(input_uuid)
        type_uuid = None if inst is None else inst.type_uuid
        if type_uuid is None:
            return {}
        owner = WType.by_uuid(type_uuid)
        if owner is None:
            return {}
        result: dict[str, object] = {}
        for prop in WProp.all_for(owner):
            if prop.function_uuid is not None:
                result[prop.key] = cls.evaluate_for(prop.function_uuid)
            else:
                result[prop.key] = cast(object, getattr(wrapper, prop.key))
        return result

    @classmethod
    @databasemethod(commit=False)
    def evaluate_for(cls, function_uuid: UUID) -> ScalarPayload | None:
        """Fold the function over its current input object — the read-time
        entry point for rendering a function-backed prop."""
        return cls.evaluate(function_uuid, cls.materialize_input(function_uuid))

    # --- graph persistence ---

    @classmethod
    @databasemethod(commit=False)
    def _nodes(cls, function_uuid: UUID) -> list[TABLE_FunctionNodes]:
        return list(
            Database.session.scalars(
                sqla.select(TABLE_FunctionNodes)
                .where(TABLE_FunctionNodes.function_uuid == function_uuid)
                .order_by(TABLE_FunctionNodes.position)
            ).all()
        )

    @classmethod
    @databasemethod(commit=False)
    def _edges(cls, function_uuid: UUID) -> list[TABLE_FunctionEdges]:
        return list(
            Database.session.scalars(
                sqla.select(TABLE_FunctionEdges).where(
                    TABLE_FunctionEdges.function_uuid == function_uuid
                )
            ).all()
        )

    @classmethod
    @databasemethod(commit=True)
    def sync_graph(
        cls,
        function_uuid: UUID,
        nodes: Sequence[tuple[UUID | None, str, int, Mapping[str, object]]],
        edges: Sequence[tuple[UUID, int, UUID, int]],
    ) -> None:
        """Replace the function's DAG. `nodes` items are
        (uuid | None, kind, position, config); None uuid creates. `edges`
        items are (from_node_uuid, from_port, to_node_uuid, to_port)."""
        existing_nodes = cls._nodes(function_uuid)
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
        # edges are non-identity (no client uuids) — drop and rebuild
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

    # --- recompute dependency index ---

    @classmethod
    @databasemethod(commit=False)
    def sync_deps(cls, function_uuid: UUID) -> None:
        """Rebuild the function's function_deps row from its current input
        link. The input prop is a link to a T object; no link -> no row."""
        inst = Database.session.get(TABLE_Instances, function_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None or not owner.is_function:
            return
        prop = WProp.by_key(owner, INPUT_PROP_KEY)
        if prop is None:
            return
        link = Database.session.scalar(
            sqla.select(TABLE_InstanceValues.uuid).where(
                TABLE_InstanceValues.inst_uuid == function_uuid,
                TABLE_InstanceValues.prop_uuid == prop.uuid,
            )
        )
        _ = Database.session.execute(
            sqla.delete(TABLE_FunctionDeps).where(TABLE_FunctionDeps.function_uuid == function_uuid)
        )
        if link is not None:
            Database.session.add(
                TABLE_FunctionDeps(function_uuid=function_uuid, input_object_uuid=link)
            )

    # --- cross-function dependency cycle detection ---

    @classmethod
    @databasemethod(commit=False)
    def _function_instance_uuids(cls,) -> list[UUID]:
        """Every function instance uuid (instances whose type kind is
        'function')."""
        return list(
            Database.session.scalars(
                sqla.select(TABLE_Instances.uuid)
                .join(TABLE_Types, TABLE_Types.uuid == TABLE_Instances.type_uuid)
                .where(TABLE_Types.kind == WType.KIND_FUNCTION)
            ).all()
        )

    @classmethod
    @databasemethod(commit=False)
    def assert_no_dependency_cycle(cls) -> None:
        """ADR-0007 cross-function cycle check: a function A depends on B
        when A's input object type carries a prop computed by B (reading A
        transitively forces reading B). A back-edge in that graph means a
        function would recurse forever at read time. Run this on save,
        before persisting a function or binding a prop to one."""
        function_uuids = set(cls._function_instance_uuids())
        deps: dict[UUID, set[UUID]] = {}
        for function_uuid in function_uuids:
            deps[function_uuid] = set()
            input_uuid = cls.input_object_uuid(function_uuid)
            if input_uuid is None:
                continue
            inst = instances.get(input_uuid)
            type_uuid = None if inst is None else inst.type_uuid
            if type_uuid is None:
                continue
            owner = WType.by_uuid(type_uuid)
            if owner is None:
                continue
            for prop in WProp.all_for(owner):
                if prop.function_uuid is not None and prop.function_uuid in function_uuids:
                    deps[function_uuid].add(prop.function_uuid)
        cls._assert_acyclic(deps)

    @classmethod
    def _assert_acyclic(cls, deps: Mapping[UUID, set[UUID]]) -> None:
        """White/gray/black DFS — a gray re-entry is a back-edge (cycle)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[UUID, int] = {u: WHITE for u in deps}

        def visit(u: UUID) -> None:
            color[u] = GRAY
            for v in deps.get(u, ()):
                if color.get(v, WHITE) == GRAY:
                    _error("function dependency cycle detected")
                if color.get(v, WHITE) == WHITE:
                    visit(v)
            color[u] = BLACK

        for u in deps:
            if color[u] == WHITE:
                visit(u)

    # --- public readers (for the FunctionView render) ---

    @classmethod
    @databasemethod(commit=False)
    def nodes(cls, function_uuid: UUID) -> list[TABLE_FunctionNodes]:
        return cls._nodes(function_uuid)

    @classmethod
    @databasemethod(commit=False)
    def edges(cls, function_uuid: UUID) -> list[TABLE_FunctionEdges]:
        return cls._edges(function_uuid)

    @classmethod
    @databasemethod(commit=False)
    def instance_uuids(cls) -> list[UUID]:
        return cls._function_instance_uuids()
