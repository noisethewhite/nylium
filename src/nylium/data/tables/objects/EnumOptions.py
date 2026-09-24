"""EnumOptions table store for EnumOption."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database.Table import Row, Table
from nylium.data.rows import EnumOption

class EnumOptions(Table[UUID, EnumOption]):
    """The enum_options table as a Mapping of writable options."""

    __row__: ClassVar[type[Row]] = EnumOption

enum_options = EnumOptions()
