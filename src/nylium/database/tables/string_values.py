# Scalar values live in one table per value kind, keyed by (instance, prop).
# No row = the prop has no value on that instance.
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class StringValues(Base):
    __tablename__: str = "string_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
