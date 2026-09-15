"""WFunction: the Function<T, R> type kind (ADR-0007).

A function type is parameterized on an input object type ``T`` and a
scalar output ``R`` (``Function<Invoice, Numeric>``). A function
*instance* carries one pinned prop ``input`` (a link to a ``T`` object)
and a body — an action DAG stored in ``function_nodes`` / ``function_edges``
keyed by the instance uuid.

The surface is composed from single-concern modules (ADR-0018):
constants (node vocabulary), typing (arity/output rules), validation
(DAG checks), evaluation (the pure interpreter), inputs (materialization),
persistence (graph + recompute deps) and lifecycle (type creation).

No ``eval``, no third-party deps — each node kind is a closed, hand
written operation, so the arbitrary-code surface is structurally shut.
"""
from __future__ import annotations

from nylium.objects.wfunction.constants import INPUT_PROP_KEY
from nylium.objects.wfunction.function import WFunction

__all__ = [
    "INPUT_PROP_KEY",
    "WFunction",
]
