from __future__ import annotations
from nylium.objects.scalar_type_names import INTEGER
from nylium.data.rows import IntegerValue
from nylium.data.tables import IntegerValues
from nylium.objects.NyScalar import NyScalar
from typing import final


@final
class NyInteger(NyScalar):
    TYPE_NAME = INTEGER
    PYTHON_TYPE = int
    TABLE = IntegerValue
    SCALAR = IntegerValues
    ICON = "tag"
