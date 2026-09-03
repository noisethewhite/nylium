from datetime import time
from uuid import UUID

from sqlalchemy import ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class TimeValues(Base):
    __tablename__: str = "time_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[time] = mapped_column(Time, nullable=False)
