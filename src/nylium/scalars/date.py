"""Date cell wrapper — TABLE_DateValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.date_values import TABLE_DateValues


@final
class Date(Scalar):
    TABLE = TABLE_DateValues
