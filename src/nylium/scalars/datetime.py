"""Datetime cell wrapper — TABLE_DatetimeValues."""
from __future__ import annotations

from typing import final

from nylium.scalars.base import Scalar
from nylium.tables.values.datetime_values import TABLE_DatetimeValues


@final
class Datetime(Scalar):
    TABLE = TABLE_DatetimeValues
