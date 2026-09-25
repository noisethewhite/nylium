from __future__ import annotations
from nylium.data.types.MonthDayTime import MonthDayTime
from nylium.data.rows import MonthDayTimeValue
from nylium.data.tables import MonthDayTimeValues
from nylium.ny.NyScalar import NyScalar
from nylium.ny.NyScalar import ScalarPayload
from typing import final
from typing import override
from nylium.Constants import Constants


@final
class NyMonthDayTime(NyScalar):
    """Month/day plus wall-clock time, stored as "MM-DDTHH:MM"."""

    TYPE_NAME = Constants.Scalar.MONTH_DAY_TIME
    PYTHON_TYPE = MonthDayTime
    TABLE = MonthDayTimeValue
    SCALAR = MonthDayTimeValues
    ICON = "alarm"

    @override
    @classmethod
    def to_storage(cls, value: ScalarPayload) -> object:
        return str(value)

    @override
    @classmethod
    def from_storage(cls, raw: object) -> ScalarPayload:
        return MonthDayTime.parse(str(raw))
