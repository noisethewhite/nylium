"""InstanceValue mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.row import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class InstanceValue(Row):
    __tablename__: ClassVar[str] = "instance_values"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False, index=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
