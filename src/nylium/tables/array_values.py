# Array elements: the array itself is an instance (of an array type);
# rows map (array instance, index) -> element. The element is either a box
# instance (scalar/nested-array), a referenced user-type instance, or — for
# Array<File/Document/Image> (ADR-0008) — a files.uuid. So value_uuid is a
# bare uuid, not an FK: files aren't instances and would violate the
# instances FK. Cleanup is manual in WArray, not DB-cascaded.
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import Base


class ArrayValues(Base):
    __tablename__: str = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(nullable=False)
