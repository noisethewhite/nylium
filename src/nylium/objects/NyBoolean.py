from __future__ import annotations
from nylium.data.rows import BooleanValue
from nylium.data.tables import BooleanValues
from nylium.objects.NyScalar import NyScalar
from typing import final
from nylium.Constants import Constants


@final
class NyBoolean(NyScalar):
    TYPE_NAME = Constants.Scalar.BOOLEAN
    PYTHON_TYPE = bool
    TABLE = BooleanValue
    SCALAR = BooleanValues
    ICON = "toggle_on"
