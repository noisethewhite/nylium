"""MonthDayTime cell wrapper — TABLE_MonthDayTimeValues (stored as "MM-DDTHH:MM")."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues


@final
class MonthDayTime(Scalar):
    TABLE = TABLE_MonthDayTimeValues
