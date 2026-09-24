"""FunctionEdge mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.Table import Row
from nylium.database.registry import reg

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
