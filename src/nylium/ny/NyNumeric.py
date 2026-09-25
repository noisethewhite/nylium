from __future__ import annotations
from decimal import Decimal
from nylium.data.rows import NumericValue
from nylium.data.tables import NumericValues
from nylium.ny.NyScalar import NyScalar
from typing import final
from nylium.Constants import Constants


@final
class NyNumeric(NyScalar):
    TYPE_NAME = Constants.Scalar.NUMERIC
    PYTHON_TYPE = Decimal
    TABLE = NumericValue
    SCALAR = NumericValues
    ICON = "percent"
