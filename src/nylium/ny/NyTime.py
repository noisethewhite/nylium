from __future__ import annotations
from nylium.ny.NyScalar import NyScalar
from nylium.data.rows import TimeValue
from nylium.data.tables import TimeValues
from typing import final
from datetime import time
from nylium.Constants import Constants


@final
class NyTime(NyScalar):
    TYPE_NAME = Constants.Scalar.TIME
    PYTHON_TYPE = time
    TABLE = TimeValue
    SCALAR = TimeValues
    ICON = "schedule"
