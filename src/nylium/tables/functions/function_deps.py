# Recomputation dependency index (ADR-0007): which object each function
# instance currently reads as its input. Synced whenever a function's
# `input` link changes; the ORM events consult it to know what to recompute
# when an object mutates.
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_FunctionDeps:
    __tablename__: ClassVar[str] = "function_deps"

    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    input_object_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False
    )


@databasemethod(commit=False)
def replace_dep(function_uuid: UUID, input_object_uuid: UUID | None) -> None:
    """Rebuild the function's dep row: drop the old one, insert when the
    input link is set (ADR-0019)."""
    _ = Database.session.execute(
        sqla.delete(TABLE_FunctionDeps).where(
            TABLE_FunctionDeps.function_uuid == function_uuid
        )
    )
    if input_object_uuid is not None:
        Database.session.add(
            TABLE_FunctionDeps(
                function_uuid=function_uuid, input_object_uuid=input_object_uuid
            )
        )
