# Year-less calendar stamps (MonthDay/MonthDayTime) have no native
# column type — they cross the boundary as their text stamp form.
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_MonthDayTimeValues:
    __tablename__: ClassVar[str] = "monthdaytime_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
