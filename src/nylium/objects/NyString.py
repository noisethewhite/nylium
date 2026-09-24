from __future__ import annotations
from nylium.objects.NyScalar import NyScalar
from nylium.objects.scalar_type_names import STRING
from nylium.data.rows import StringValue
from nylium.data.tables import StringValues
from typing import final


@final
class NyString(NyScalar):
    TYPE_NAME = STRING
    PYTHON_TYPE = str
    TABLE = StringValue
    SCALAR = StringValues
    ICON = "text_fields"
