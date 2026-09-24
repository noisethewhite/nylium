"""FunctionEdges table store for FunctionEdge."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.Row import mapper
from nylium.database.Table import Row, Table
from nylium.data.rows import FunctionEdge

class FunctionEdges(Table[UUID, FunctionEdge]):
    """The function_edges table as a store of DAG edges."""

    __row__: ClassVar[type[Row]] = FunctionEdge

    @classmethod
    @Database.use_same_session
    def edges_of(cls, function_uuid: UUID) -> list[FunctionEdge]:
        c = mapper(FunctionEdge).columns
        return list(
            Database.scalars(
                sqla.select(FunctionEdge).where(c.function_uuid == function_uuid)
            ).all()
        )

function_edges = FunctionEdges()
