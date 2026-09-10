from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_BooleanValues:
    __tablename__: ClassVar[str] = "boolean_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[bool] = mapped_column(nullable=False)
