# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One trait's decor: a writable snapshot of a TABLE_TraitDecor row (Row class only)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.decor.table_trait_decor import TABLE_TraitDecor


class TraitDecor(Row):
    """One trait's decor: a writable snapshot of a TABLE_TraitDecor row."""

    __table__: ClassVar[type[object]] = TABLE_TraitDecor

    uuid: UUID
    color: str
