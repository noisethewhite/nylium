# Recomputation dependency index (ADR-0007): which object each function
# instance currently reads as its input. Synced whenever a function's
# `input` link changes; the ORM events consult it to know what to recompute
# when an object mutates.
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import Base


class FunctionDeps(Base):
    __tablename__: str = "function_deps"

    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    input_object_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False
    )
