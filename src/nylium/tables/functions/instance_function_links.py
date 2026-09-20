# Instance-level function binding (ADR-0029): which function computes a
# specific prop of a specific object. Keyed by (inst_uuid, prop_uuid) —
# "one function per (owner, prop)" — mirroring instance_values' link
# shape, but the target is a Function<T,R> instance instead of an object.
# This replaces the type-level props.function_uuid column: different
# instances of one type may bind different functions (or none).
# The statement helpers moved to objects/wfunction/function_links.py
# (ADR-0030 phase C).
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_InstanceFunctionLinks:
    __tablename__: ClassVar[str] = "instance_function_links"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
