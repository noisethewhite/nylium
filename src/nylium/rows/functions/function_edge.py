# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One function DAG edge: a writable snapshot of a TABLE_FunctionEdges row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.functions.function_edges import TABLE_FunctionEdges


class FunctionEdge(Row):
    """One function DAG edge: a writable snapshot of a TABLE_FunctionEdges row."""

    __table__: ClassVar[type[object]] = TABLE_FunctionEdges

    uuid: UUID
    function_uuid: UUID
    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int
