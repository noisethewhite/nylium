# Array elements: the array itself is an instance (of an array type);
# rows map (array instance, index) -> element instance.
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class ArrayValues(Base):
    __tablename__: str = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False
    )
