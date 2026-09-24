from __future__ import annotations
from nylium.objects.scalar_type_names import MONTH_DAY
from nylium.objects.MonthDay import MonthDay
from nylium.data.rows import MonthDayValue
from nylium.data.tables import MonthDayValues
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyScalar import ScalarPayload
from typing import final
from typing import override


@final
class NyMonthDay(NyScalar):
    """Month/day without a year, stored as its "MM-DD" stamp."""

    TYPE_NAME = MONTH_DAY
    PYTHON_TYPE = MonthDay
    TABLE = MonthDayValue
    SCALAR = MonthDayValues
    ICON = "calendar_today"

    @override
    @classmethod
    def to_storage(cls, value: ScalarPayload) -> object:
        return str(value)

    @override
    @classmethod
    def from_storage(cls, raw: object) -> ScalarPayload:
        return MonthDay.parse(str(raw))
