# Values that are references to other instances (links, nested objects,
# arrays). Keyed by (owner instance, prop) — one target per (owner, prop)
# — with the target as an indexed FK so a single target may be referenced
# from any number of owners (ADR-0028 many-to-one).
# The link-statement helpers moved to objects/wlink.py (ADR-0030 phase C):
# the objects layer decides semantics, the statements live there now.
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import ClassVar

from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_InstanceValues:
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
