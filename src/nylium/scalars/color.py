"""Color cell wrapper — TABLE_StringValues (3-byte #RRGGBB hex)."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.string_values import TABLE_StringValues


@final
class Color(Scalar):
    TABLE = TABLE_StringValues
