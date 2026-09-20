"""Integer cell wrapper — TABLE_IntegerValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.integer_values import TABLE_IntegerValues


@final
class Integer(Scalar):
    TABLE = TABLE_IntegerValues
