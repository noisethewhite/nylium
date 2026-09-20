"""String cell wrapper — TABLE_StringValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.string_values import TABLE_StringValues


@final
class String(Scalar):
    TABLE = TABLE_StringValues
