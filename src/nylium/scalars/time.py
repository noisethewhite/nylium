"""Time cell wrapper — TABLE_TimeValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.time_values import TABLE_TimeValues


@final
class Time(Scalar):
    TABLE = TABLE_TimeValues
