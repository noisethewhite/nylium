"""NyFunction: the Function<T, R> type kind (ADR-0007 / ADR-0029).

A function type is parameterized on an owner object type ``T`` and a
scalar output ``R`` (``Function<Receipt, Numeric>``). A function
*instance* carries only a ``name`` prop (ADR-0029 removed the ``input``
link) and a body — an action DAG stored in ``function_nodes`` /
``function_edges`` keyed by the instance uuid. Its input is resolved at
read time from the sibling props of the object it is bound into
(``instance_function_links``).

The surface is composed from single-concern modules (ADR-0018):
constants (node vocabulary), typing (arity/output rules), validation
(DAG checks), evaluation (the pure interpreter), inputs (owner-sibling
materialization), persistence (graph + local cycle check) and lifecycle
(type creation). ``nylium.data.views`` holds the FunctionView/node/edge wire
DTOs; this package does NOT re-export them — call sites import them from
``nylium.data.views``, which breaks the nyfunction<->views import cycle.

No ``eval``, no third-party deps — each node kind is a closed, hand
written operation, so the arbitrary-code surface is structurally shut.
"""
from __future__ import annotations

from nylium.ny.nyfunction.NyFunction import NyFunction
from nylium.ny.nyfunction.typing import NODE_ARITY, node_output_type
from nylium.ny.nyfunction.constants import NodeType, fail, is_array_type, is_numeric_scalar
from nylium.ny.nyfunction.evaluation import evaluate
from nylium.ny.nyfunction.inputs import evaluate_for, materialize_owner
from nylium.ny.nyfunction.lifecycle import ensure_type, is_function
from nylium.ny.nyfunction.validation import validate_graph, topo_sort

__all__ = [
    "NODE_ARITY",
    "NodeType",
    "NyFunction",
    "ensure_type",
    "evaluate",
    "evaluate_for",
    "fail",
    "is_array_type",
    "is_function",
    "is_numeric_scalar",
    "materialize_owner",
    "node_output_type",
    "topo_sort",
    "validate_graph",
]
