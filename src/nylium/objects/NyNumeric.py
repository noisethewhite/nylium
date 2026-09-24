from __future__ import annotations
from decimal import Decimal
from nylium.objects.scalar_type_names import NUMERIC
from nylium.data.rows import NumericValue
from nylium.data.tables import NumericValues
from nylium.objects.NyScalar import NyScalar
from typing import final


@final
class NyNumeric(NyScalar):
    TYPE_NAME = NUMERIC
    PYTHON_TYPE = Decimal
    TABLE = NumericValue
    SCALAR = NumericValues
    ICON = "percent"
