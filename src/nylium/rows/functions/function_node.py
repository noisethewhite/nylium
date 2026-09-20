# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One function DAG node: a writable snapshot of a TABLE_FunctionNodes row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes


class FunctionNode(Row):
    """One function DAG node: a writable snapshot of a TABLE_FunctionNodes row."""

    __table__: ClassVar[type[object]] = TABLE_FunctionNodes

    uuid: UUID
    function_uuid: UUID
    kind: str
    position: int
    config: dict[str, object]
