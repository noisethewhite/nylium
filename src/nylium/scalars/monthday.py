"""MonthDay cell wrapper — TABLE_MonthDayValues (stored as "MM-DD")."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.monthday_values import TABLE_MonthDayValues


@final
class MonthDay(Scalar):
    TABLE = TABLE_MonthDayValues
