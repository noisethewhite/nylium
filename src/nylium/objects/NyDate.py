from __future__ import annotations
from nylium.objects.scalar_type_names import DATE
from nylium.data.rows import DateValue
from nylium.data.tables import DateValues
from nylium.objects.NyScalar import NyScalar
from datetime import date
from typing import final


@final
class NyDate(NyScalar):
    TYPE_NAME = DATE
    PYTHON_TYPE = date
    TABLE = DateValue
    SCALAR = DateValues
    ICON = "calendar_month"
