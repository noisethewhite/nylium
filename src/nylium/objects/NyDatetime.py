from __future__ import annotations
from nylium.objects.scalar_type_names import DATETIME
from nylium.data.rows import DatetimeValue
from nylium.data.tables import DatetimeValues
from nylium.objects.NyScalar import NyScalar
from datetime import datetime
from typing import final


@final
class NyDatetime(NyScalar):
    TYPE_NAME = DATETIME
    PYTHON_TYPE = datetime
    TABLE = DatetimeValue
    SCALAR = DatetimeValues
    ICON = "calendar_clock"
