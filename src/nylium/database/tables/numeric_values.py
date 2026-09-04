from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class NumericValues(Base):
    __tablename__: str = "numeric_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[Decimal] = mapped_column(nullable=False)
    # unit part name as entered (for `Numeric<Unit>` props); NULL means
    # the unit's base part or a plain unitless Numeric
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
