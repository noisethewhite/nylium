"""WFunction: the composed surface (ADR-0018) — a flat facade over the
per-concern modules: lifecycle (Function<T, R> materialization), typing
(node arity/output rules), validation (DAG checks), evaluation (the
interpreter), inputs (materialization), persistence (graph + deps).

Every method is behaviorally a module function — the class carries no
instance state and is never instantiated — so the facade binds them with
``staticmethod`` instead of composing mixins: there is no cross-mixin
state to share, and a plain binding keeps the checker honest without
TYPE_CHECKING-base gymnastics."""
from __future__ import annotations

from typing import ClassVar, final

from nylium.objects.wfunction.evaluation import evaluate
from nylium.objects.wfunction.inputs import (
    evaluate_for,
    input_object_uuid,
    materialize_input,
)
from nylium.objects.wfunction.lifecycle import ensure_type, is_function
from nylium.objects.wfunction.persistence import (
    assert_no_dependency_cycle,
    edges,
    instance_uuids,
    nodes,
    sync_deps,
    sync_graph,
)
from nylium.objects.wfunction.typing import NODE_ARITY, node_output_type
from nylium.objects.wfunction.validation import validate_graph


@final
class WFunction:
    """Function type / graph surface (ADR-0007)."""

    # kind -> input arity (the node whitelist; owned by typing.py).
    NODES: ClassVar[dict[str, int]] = NODE_ARITY

    # --- lifecycle ---
    is_function = staticmethod(is_function)
    ensure_type = staticmethod(ensure_type)

    # --- node config ---
    node_output_type = staticmethod(node_output_type)

    # --- graph validation ---
    validate_graph = staticmethod(validate_graph)

    # --- evaluation ---
    evaluate = staticmethod(evaluate)

    # --- input materialization ---
    input_object_uuid = staticmethod(input_object_uuid)
    materialize_input = staticmethod(materialize_input)
    evaluate_for = staticmethod(evaluate_for)

    # --- graph persistence ---
    sync_graph = staticmethod(sync_graph)
    sync_deps = staticmethod(sync_deps)

    # --- cross-function dependency cycle detection ---
    assert_no_dependency_cycle = staticmethod(assert_no_dependency_cycle)

    # --- public readers (for the FunctionView render) ---
    nodes = staticmethod(nodes)
    edges = staticmethod(edges)
    instance_uuids = staticmethod(instance_uuids)
