# A reference to a file entity held by an instance's file-typed prop
# (ADR-0008). Mirrors instance_values, but the target is files.uuid, not
# instances.uuid — files are not objects. Keyed by (owner instance, prop):
# one prop holds one file reference, and a file may be referenced from many
# props (unlike instance_values, whose target-uuid PK forbids multi-ref).
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.tables.base import Base


class FileValues(Base):
    __tablename__: str = "file_values"

    file_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("files.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
