# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One instance: a writable snapshot of a TABLE_Instances row (Row class only)."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.table_instances import TABLE_Instances
from nylium.tables.objects.types import types


class Instance(Row):
    """One instance: a writable snapshot of a TABLE_Instances row."""

    __table__: ClassVar[type[object]] = TABLE_Instances

    uuid: UUID
    type_uuid: UUID
    name: str
    plural_name: str
    owner_object_uuid: UUID | None
    owner_prop_uuid: UUID | None
    created_at: datetime
    modified_at: datetime

    @property
    def type_name(self) -> str:
        """The instance's type name; ``<dangling>`` if the type row is gone."""
        t = types.get(self.type_uuid)
        return "<dangling>" if t is None else t.name
