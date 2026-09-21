"""The function_edges table: FunctionEdge (mapped Row) + FunctionEdges (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class FunctionEdge(Row):
    __tablename__: ClassVar[str] = "function_edges"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )
    from_node_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("function_nodes.uuid", ondelete="CASCADE"), nullable=False
    )
    from_port: Mapped[int] = mapped_column(Integer, nullable=False, default=0, kw_only=True)
    to_node_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("function_nodes.uuid", ondelete="CASCADE"), nullable=False
    )
    to_port: Mapped[int] = mapped_column(Integer, nullable=False, default=0, kw_only=True)


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
