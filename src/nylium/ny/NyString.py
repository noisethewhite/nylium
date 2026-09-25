from __future__ import annotations
from nylium.ny.NyScalar import NyScalar
from nylium.data.rows import StringValue
from nylium.data.tables import StringValues
from typing import final
from nylium.Constants import Constants


@final
class NyString(NyScalar):
    TYPE_NAME = Constants.Scalar.STRING
    PYTHON_TYPE = str
    TABLE = StringValue
    SCALAR = StringValues
    ICON = "text_fields"
