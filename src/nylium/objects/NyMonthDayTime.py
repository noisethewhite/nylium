from __future__ import annotations
from nylium.objects.scalar_type_names import MONTH_DAY_TIME
from nylium.objects.MonthDayTime import MonthDayTime
from nylium.data.rows import MonthDayTimeValue
from nylium.data.tables import MonthDayTimeValues
from nylium.objects.NyScalar import NyScalar
from nylium.objects.nyscalar import ScalarPayload
from typing import final
from typing import override


@final
class NyMonthDayTime(NyScalar):
    """Month/day plus wall-clock time, stored as "MM-DDTHH:MM"."""

    TYPE_NAME = MONTH_DAY_TIME
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
