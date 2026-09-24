from __future__ import annotations
from typing import ClassVar
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyScalar import ScalarPayload
from nylium.data.rows import StringValue
from nylium.data.tables import StringValues
from typing import cast
from typing import final
from typing import override
import re
from nylium.Constants import Constants


@final
class NyColor(NyScalar):
    """3-byte RGB hex ``#RRGGBB`` (ADR-0005): first-class scalar and the
    backing type of type/icon/tag colors. Stored in StringValue."""

    TYPE_NAME = Constants.Scalar.COLOR
    PYTHON_TYPE = str
    TABLE = StringValue
    SCALAR = StringValues
    ICON = "palette"

    HEX_RE: ClassVar[re.Pattern[str]] = re.compile(r"^#[0-9A-Fa-f]{6}$")
    # Neutral default; the named palette below exists only to migrate
    # pre-ADR-0005 rows that stored palette keys instead of hex
    DEFAULT: ClassVar[str] = "#9e9e9e"
    LEGACY_PALETTE: ClassVar[dict[str, str]] = {
        "gray": "#9e9e9e",
        "red": "#e5534b",
        "orange": "#e0823d",
        "amber": "#d9a514",
        "green": "#57ab5a",
        "teal": "#39c5cf",
        "blue": "#539bf5",
        "purple": "#b083f0",
        "pink": "#e275ad",
    }

    @override
    @classmethod
    def check(cls, value: ScalarPayload) -> None:
        if not cls.HEX_RE.fullmatch(cast(str, value)):
            raise ValueError(f"Color takes #RRGGBB hex, got {value!r}")
