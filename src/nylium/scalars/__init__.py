"""Scalar cell wrappers — one class per scalar value kind (ADR-0030).

Value-side read/write/clear for the nine scalar ``*Values`` tables,
verbatim-ported from the former ``tables.values.cells`` / ``numeric_values``
helpers. Import the concrete wrapper (``Integer``, ``String``, …) instead of
the old ``cells.read(table, …)`` calls.
"""
from nylium.scalars.base import Scalar, ScalarCellsTable
from nylium.scalars.boolean import Boolean
from nylium.scalars.color import Color
from nylium.scalars.date import Date
from nylium.scalars.datetime import Datetime
from nylium.scalars.integer import Integer
from nylium.scalars.monthday import MonthDay
from nylium.scalars.monthdaytime import MonthDayTime
from nylium.scalars.numeric import Numeric
from nylium.scalars.string import String
from nylium.scalars.time import Time

__all__ = [
    "Scalar",
    "ScalarCellsTable",
    "Boolean",
    "Color",
    "Date",
    "Datetime",
    "Integer",
    "MonthDay",
    "MonthDayTime",
    "Numeric",
    "String",
    "Time",
]
