# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One attach edge: a writable snapshot of a TABLE_TypeTraits row (Row class only)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.table_type_traits import TABLE_TypeTraits


class TypeTrait(Row):
    """One attach edge: a writable snapshot of a TABLE_TypeTraits row."""

    __table__: ClassVar[type[object]] = TABLE_TypeTraits

    type_uuid: UUID
    trait_uuid: UUID
    position: int
