from __future__ import annotations
from nylium.data.rows import DateValue
from nylium.data.tables import DateValues
from nylium.objects.NyScalar import NyScalar
from datetime import date
from typing import final
from nylium.Constants import Constants


@final
class NyDate(NyScalar):
    TYPE_NAME = Constants.Scalar.DATE
    PYTHON_TYPE = date
    TABLE = DateValue
    SCALAR = DateValues
    ICON = "calendar_month"
