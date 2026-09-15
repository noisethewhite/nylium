"""WFunction graph persistence and the recompute dependency index
(ADR-0007): sync_graph/sync_deps, the public node/edge readers for the
FunctionView render, and the cross-function dependency cycle check."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from nylium.database import databasemethod
from nylium.tables import instances
from nylium.tables.functions import graph
from nylium.tables.functions.function_deps import replace_dep
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes
from nylium.tables.objects.instances import get as instance_get
from nylium.tables.objects.instances import uuids_of_kind
from nylium.tables.values.instance_values import link_for
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType
from nylium.objects.wfunction.constants import INPUT_PROP_KEY, fail
from nylium.objects.wfunction.inputs import input_object_uuid


@databasemethod(commit=True)
def sync_graph(
    function_uuid: UUID,
    nodes: Sequence[tuple[UUID | None, str, int, Mapping[str, object]]],
    edges: Sequence[tuple[UUID, int, UUID, int]],
) -> None:
    """Replace the function's DAG. `nodes` items are
    (uuid | None, kind, position, config); None uuid creates. `edges`
    items are (from_node_uuid, from_port, to_node_uuid, to_port)."""
    graph.sync_graph(function_uuid, nodes, edges)


@databasemethod(commit=False)
def sync_deps(function_uuid: UUID) -> None:
    """Rebuild the function's function_deps row from its current input
    link. The input prop is a link to a T object; no link -> no row."""
    inst = instance_get(function_uuid)
    if inst is None:
        return
    owner = WType.by_uuid(inst.type_uuid)
    if owner is None or not owner.is_function:
        return
    prop = WProp.by_key(owner, INPUT_PROP_KEY)
    if prop is None:
        return
    link = link_for(function_uuid, prop.uuid)
    replace_dep(function_uuid, None if link is None else link.uuid)


@databasemethod(commit=False)
def _function_instance_uuids() -> list[UUID]:
    """Every function instance uuid (instances whose type kind is
    'function')."""
    return uuids_of_kind(WType.KIND_FUNCTION)


@databasemethod(commit=False)
def assert_no_dependency_cycle() -> None:
    """ADR-0007 cross-function cycle check: a function A depends on B
    when A's input object type carries a prop computed by B (reading A
    transitively forces reading B). A back-edge in that graph means a
    function would recurse forever at read time. Run this on save,
    before persisting a function or binding a prop to one."""
    function_uuids = set(_function_instance_uuids())
    deps: dict[UUID, set[UUID]] = {}
    for function_uuid in function_uuids:
        deps[function_uuid] = set()
        input_uuid = input_object_uuid(function_uuid)
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


@databasemethod(commit=False)
def nodes(function_uuid: UUID) -> list[TABLE_FunctionNodes]:
    return graph.nodes_of(function_uuid)


@databasemethod(commit=False)
def edges(function_uuid: UUID) -> list[TABLE_FunctionEdges]:
    return graph.edges_of(function_uuid)


@databasemethod(commit=False)
def instance_uuids() -> list[UUID]:
    return _function_instance_uuids()
