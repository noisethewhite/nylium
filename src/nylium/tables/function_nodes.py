# A node in a function's action DAG (ADR-0007). Nodes are the whitelisted
# operations; edges carry the dataflow between them. `config` is a JSON
# object whose shape depends on `kind` (get_prop -> {key}, const -> {value},
# cast -> {target}, reductions/arithmetic -> {}).
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import Base


class FunctionNodes(Base):
    __tablename__: str = "function_nodes"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    config: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
