"""NyScalar base + the builtin scalar peer types.

These are marker classes, not value wrappers: annotate props with them
(`name: NyString`), assign plain python values (`obj.name = "Max"`).
Each peer owns its binding to the nylium type system (TYPE_NAME),
the accepted python type (PYTHON_TYPE) and its storage table (TABLE).

File-level exception to one-class-per-file: these are peer types
mirroring the scalar set of nylium's own `types` table.

The resolver accepts ONLY NyScalar subclasses, NyObject subclasses and
list[...] of those — the prop type world is closed by construction.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from nylium.objects.MonthDay import MonthDay
from nylium.objects.MonthDayTime import MonthDayTime
from nylium.data.rows import BooleanValue
from nylium.data.rows import DateValue
from nylium.data.rows import DatetimeValue
from nylium.data.rows import IntegerValue
from nylium.data.rows import MonthDayTimeValue
from nylium.data.rows import MonthDayValue
from nylium.data.rows import NumericValue
from nylium.data.rows import StringValue
from nylium.data.rows import TimeValue

VALUE_PROP_KEY = "value"

ScalarPayload = str | int | Decimal | bool | datetime | date | time | MonthDay | MonthDayTime
ScalarTable = (
    StringValue | IntegerValue | NumericValue | BooleanValue | DatetimeValue
    | DateValue | TimeValue | MonthDayValue | MonthDayTimeValue
)
