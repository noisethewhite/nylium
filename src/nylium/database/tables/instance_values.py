# Values that are references to other instances (links, nested objects,
# arrays). The referenced instance's own uuid doubles as this row's pk.
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class InstanceValues(Base):
    __tablename__: str = "instance_values"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )
