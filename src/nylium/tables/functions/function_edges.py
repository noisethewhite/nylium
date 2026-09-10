# Dataflow edges of a function's action DAG (ADR-0007): a node output port
# feeds a node input port. v1 nodes have a single output (from_port is
# informational today but kept so branching needs no migration later).
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_FunctionEdges:
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
