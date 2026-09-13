# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One type's decor: a writable snapshot of a TABLE_TypeDecor row (Row class only)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.decor.table_type_decor import TABLE_TypeDecor


class TypeDecor(Row):
    """One type's decor: a writable snapshot of a TABLE_TypeDecor row."""

    __table__: ClassVar[type[object]] = TABLE_TypeDecor

    uuid: UUID
    plural_name: str
    icon: str
    color: str
