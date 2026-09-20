"""Function edges store — DAG edge reads (ADR-0031).

Moved from ``objects/wfunction/graph.py`` (ADR-0030 phase C); the
``function_edges`` table module keeps only the ``TABLE_*`` definition.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.functions.function_edge import FunctionEdge
from nylium.tables.functions.function_edges import TABLE_FunctionEdges


class FunctionEdges(Table[UUID, FunctionEdge]):
    """The function_edges table as a store of DAG edges."""

    __row__: ClassVar[type[Row]] = FunctionEdge

    @classmethod
    @Database.use_same_session
    def edges_of(cls, function_uuid: UUID) -> list[TABLE_FunctionEdges]:
        """The function's dataflow edges."""
        return list(
            Database.scalars(
                sqla.select(TABLE_FunctionEdges).where(
                    TABLE_FunctionEdges.function_uuid == function_uuid
                )
            ).all()
        )


function_edges = FunctionEdges()
