"""FileValue mapped row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from nylium.database.row import Row
from nylium.database.registry import reg

@reg.mapped_as_dataclass
class FileValue(Row):
    __tablename__: ClassVar[str] = "file_values"

    file_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("files.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
