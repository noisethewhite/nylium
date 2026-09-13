"""The props table as a Mapping of writable props (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row, Table
from nylium.tables.objects.prop import Prop as Prop
from nylium.tables.objects.table_props import TABLE_Props as TABLE_Props


class Props(Table[UUID, Prop]):
    """The props table as a Mapping of writable props."""

    __row__: ClassVar[type[Row]] = Prop


props = Props()
