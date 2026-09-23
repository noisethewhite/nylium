"""WFunction: the Function<T, R> type kind (ADR-0007 / ADR-0029).

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
(type creation). views holds the FunctionView/node/edge wire DTOs —
imported after WFunction, since objectview pulls this package mid-init.

No ``eval``, no third-party deps — each node kind is a closed, hand
written operation, so the arbitrary-code surface is structurally shut.
"""
from __future__ import annotations

from nylium.objects.wfunction.function import WFunction
from nylium.objects.wfunction.views import (
    FunctionEdgeView,
    FunctionNodeView,
    FunctionView,
)

__all__ = [
    "FunctionEdgeView",
    "FunctionNodeView",
    "FunctionView",
    "WFunction",
]
