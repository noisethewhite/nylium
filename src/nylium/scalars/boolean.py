"""Boolean cell wrapper — TABLE_BooleanValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.boolean_values import TABLE_BooleanValues


@final
class Boolean(Scalar):
    TABLE = TABLE_BooleanValues
