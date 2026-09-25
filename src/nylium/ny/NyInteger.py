from __future__ import annotations
from nylium.data.rows import IntegerValue
from nylium.data.tables import IntegerValues
from nylium.ny.NyScalar import NyScalar
from typing import final
from nylium.Constants import Constants


@final
class NyInteger(NyScalar):
    TYPE_NAME = Constants.Scalar.INTEGER
    PYTHON_TYPE = int
    TABLE = IntegerValue
    SCALAR = IntegerValues
    ICON = "tag"
