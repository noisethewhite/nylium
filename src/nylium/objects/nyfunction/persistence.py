"""NyFunction graph persistence and the local dependency cycle check
(ADR-0029): sync_graph, the public node/edge readers for the FunctionView
render, and the per-owner cross-function dependency cycle detection.

ADR-0029 removed the `function_deps` input-object index: a function's
input is now the sibling props of the object it is bound into, so the
dependency graph is local to a single owner's prop graph. A function `A`
(bound to prop `P` of owner `O`) reads a sibling `Q` that is itself
computed by `B` (bound to `Q` on the same owner) — that is an edge A→B.
A back-edge means a function would recurse forever at read time."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from nylium.database import Database
from nylium.data.rows import FunctionEdge
from nylium.data.rows import FunctionNode
from nylium.data.tables import FunctionEdges
from nylium.data.tables import FunctionNodes
from nylium.data.tables import InstanceFunctionLinks
from nylium.data.tables import instances
from nylium.objects.navigation import instance_uuids_of_kind
from nylium.objects.nyprop import NyProp
from nylium.objects.NyType import NyType
from nylium.objects.nyfunction.constants import NODE_GET_PROP, fail


@Database.commit_after_this
def sync_graph(
    function_uuid: UUID,
    nodes: Sequence[tuple[UUID | None, str, int, Mapping[str, object]]],
    edges: Sequence[tuple[UUID, int, UUID, int]],
) -> None:
    """Replace the function's DAG. `nodes` items are
    (uuid | None, kind, position, config); None uuid creates. `edges`
    items are (from_node_uuid, from_port, to_node_uuid, to_port)."""
    FunctionNodes.sync_graph(function_uuid, nodes, edges)


@Database.use_same_session
def _function_instance_uuids() -> list[UUID]:
    """Every function instance uuid (instances whose type kind is
    'function')."""
    return instance_uuids_of_kind(NyType.KIND_FUNCTION)


@Database.use_same_session
def assert_no_dependency_cycle(inst_uuid: UUID) -> None:
    """ADR-0029 local cycle check: within one owner, build the function
    dependency graph and refuse a back-edge. Function A (bound to prop P)
    depends on function B when A's DAG reads (via `get_prop`) a sibling
    prop that B computes on the same owner. A cycle would recurse forever
    at read time. Run on bind and on function DAG save."""
    # prop_uuid -> function_uuid bound on this owner
    bindings = {prop_uuid: fn_uuid for prop_uuid, fn_uuid in InstanceFunctionLinks.function_links_of_instance(inst_uuid)}
    if not bindings:
        return
    # prop key -> prop_uuid on the owner (to map get_prop keys back)
    inst = instances.get(inst_uuid)
    type_uuid = None if inst is None else inst.type_uuid
    if type_uuid is None:
        return
    owner = NyType.by_uuid(type_uuid)
    if owner is None:
        return
    prop_uuid_by_key = {prop.key: prop.uuid for prop in NyProp.effective_for(owner)}

    deps: dict[UUID, set[UUID]] = {fn_uuid: set() for fn_uuid in bindings.values()}
    for fn_uuid in bindings.values():
        for node in FunctionNodes.nodes_of(fn_uuid):
            if node.kind != NODE_GET_PROP:
                continue
            key = node.config.get("key")
            if not isinstance(key, str):
                continue
            target_prop = prop_uuid_by_key.get(key)
            if target_prop is None:
                continue
            target_fn = bindings.get(target_prop)
            if target_fn is not None and target_fn != fn_uuid:
                deps[fn_uuid].add(target_fn)
    _assert_acyclic(deps)


def _assert_acyclic(deps: Mapping[UUID, set[UUID]]) -> None:
    """White/gray/black DFS — a gray re-entry is a back-edge (cycle)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[UUID, int] = {u: WHITE for u in deps}

    def visit(u: UUID) -> None:
        color[u] = GRAY
        for v in deps.get(u, ()):
            if color.get(v, WHITE) == GRAY:
                fail("function dependency cycle detected")
            if color.get(v, WHITE) == WHITE:
                visit(v)
        color[u] = BLACK

    for u in deps:
        if color[u] == WHITE:
            visit(u)


# --- public readers (for the FunctionView render) ---


@Database.use_same_session
def nodes(function_uuid: UUID) -> list[FunctionNode]:
    return FunctionNodes.nodes_of(function_uuid)


@Database.use_same_session
def edges(function_uuid: UUID) -> list[FunctionEdge]:
    return FunctionEdges.edges_of(function_uuid)


@Database.use_same_session
def instance_uuids() -> list[UUID]:
    return _function_instance_uuids()
