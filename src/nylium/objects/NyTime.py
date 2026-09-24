from __future__ import annotations
from nylium.objects.NyScalar import NyScalar
from nylium.objects.scalar_type_names import TIME
from nylium.data.rows import TimeValue
from nylium.data.tables import TimeValues
from typing import final
from datetime import time


@final
class NyTime(NyScalar):
    TYPE_NAME = TIME
    PYTHON_TYPE = time
    TABLE = TimeValue
    SCALAR = TimeValues
    ICON = "schedule"
