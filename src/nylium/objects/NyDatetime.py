from __future__ import annotations
from nylium.data.rows import DatetimeValue
from nylium.data.tables import DatetimeValues
from nylium.objects.NyScalar import NyScalar
from datetime import datetime
from typing import final
from nylium.Constants import Constants


@final
class NyDatetime(NyScalar):
    TYPE_NAME = Constants.Scalar.DATETIME
    PYTHON_TYPE = datetime
    TABLE = DatetimeValue
    SCALAR = DatetimeValues
    ICON = "calendar_clock"
