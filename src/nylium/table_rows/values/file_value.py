"""The file_values table: FileValue (mapped Row) + FileValues (store).

A reference to a file entity held by an instance's file-typed prop
(ADR-0008). Mirrors instance_values, but the target is files.uuid, not
instances.uuid — files are not objects. Keyed by (owner instance, prop):
one prop holds one file reference, and a file may be referenced from many
props (unlike instance_values, whose target-uuid PK forbids multi-ref).
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.row import Row, mapper
from nylium.database.table import Table
from nylium.tables.base import reg


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


class FileValues(Table[tuple[UUID, UUID], FileValue]):
    """The file_values table as a store of file-reference rows."""

    __row__: ClassVar[type[Row]] = FileValue

    @classmethod
    @Database.use_same_session
    def file_ref_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
        """The file uuid referenced by (owner instance, prop), or None."""
        c = mapper(FileValue).columns
        return Database.scalar(
            sqla.select(c.file_uuid).where(
                c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def write_ref(
        cls, inst_uuid: UUID, prop_uuid: UUID, file_uuid: UUID | None
    ) -> None:
        """Set/clear the file reference of (owner instance, prop)."""
        c = mapper(FileValue).columns
        if file_uuid is None:
            _ = Database.execute(
                sqla.delete(FileValue).where(
                    c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
                )
            )
            return
        row = Database.get(FileValue, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                FileValue(inst_uuid=inst_uuid, prop_uuid=prop_uuid, file_uuid=file_uuid)
            )
            return
        row.file_uuid = file_uuid


file_values = FileValues()
