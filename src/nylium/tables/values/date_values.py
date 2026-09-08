from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import Base


class TABLE_DateValues(Base):
    __tablename__: str = "date_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[date] = mapped_column(Date, nullable=False)
