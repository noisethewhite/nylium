"""DatetimeValue mapped row."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.table import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class DatetimeValue(Row):
    __tablename__: ClassVar[str] = "datetime_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
