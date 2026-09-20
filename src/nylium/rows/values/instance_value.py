# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One link row: a writable snapshot of a TABLE_InstanceValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.instance_values import TABLE_InstanceValues


class InstanceValue(Row):
    """One link row: a writable snapshot of a TABLE_InstanceValues row."""

    __table__: ClassVar[type[object]] = TABLE_InstanceValues

    uuid: UUID
    prop_uuid: UUID
    inst_uuid: UUID
