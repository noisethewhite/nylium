from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg


# Self-contained file entity (ADR-0008): no FK to instances — the uuid IS
# the pointer, stable for the life of the file. The blob lives on disk at
# FILES_DIR/<uuid>. `name` is a freely renameable display name (defaults to
# the original filename on upload); `type_name` is File/Document/Image.
@reg.mapped_as_dataclass
class TABLE_Files:
    __tablename__: ClassVar[str] = "files"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_name: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
