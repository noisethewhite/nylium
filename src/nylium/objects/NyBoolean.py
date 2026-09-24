from __future__ import annotations
from nylium.objects.scalar_type_names import BOOLEAN
from nylium.data.rows import BooleanValue
from nylium.data.tables import BooleanValues
from nylium.objects.NyScalar import NyScalar
from typing import final


@final
class NyBoolean(NyScalar):
    TYPE_NAME = BOOLEAN
    PYTHON_TYPE = bool
    TABLE = BooleanValue
    SCALAR = BooleanValues
    ICON = "toggle_on"
