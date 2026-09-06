"""WScalar base + the builtin scalar peer types.

These are marker classes, not value wrappers: annotate props with them
(`name: WString`), assign plain python values (`obj.name = "Max"`).
Each peer owns its binding to the nylium type system (TYPE_NAME),
the accepted python type (PYTHON_TYPE) and its storage table (TABLE).

File-level exception to one-class-per-file: these are peer types
mirroring the scalar set of nylium's own `types` table.

The resolver accepts ONLY WScalar subclasses, WObject subclasses and
list[...] of those — the prop type world is closed by construction.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import ClassVar, cast, final, override

from nylium.database import databasemethod
from nylium.tables import (
    BooleanValues,
    DateValues,
    DatetimeValues,
    IntegerValues,
    MonthDayTimeValues,
    MonthDayValues,
    NumericValues,
    StringValues,
    TimeValues,
)
from nylium.objects.monthday import MonthDay, MonthDayTime

VALUE_PROP_KEY = "value"

ScalarPayload = str | int | Decimal | bool | datetime | date | time | MonthDay | MonthDayTime
ScalarTable = (
    StringValues | IntegerValues | NumericValues | BooleanValues | DatetimeValues
    | DateValues | TimeValues | MonthDayValues | MonthDayTimeValues
)


class WScalar:
    TYPE_NAME: ClassVar[str]
    PYTHON_TYPE: ClassVar[type[ScalarPayload]]
    TABLE: ClassVar[type[ScalarTable]]
    # Material Symbols name, rendered gray and immutable for builtins
    ICON: ClassVar[str]

    @classmethod
    def all(cls) -> "list[type[WScalar]]":
        return cls.__subclasses__()

    @classmethod
    def by_type_name(cls, type_name: str) -> "type[WScalar] | None":
        for scalar in cls.all():
            if scalar.TYPE_NAME == type_name:
                return scalar
        return None

    @classmethod
    def by_class_name(cls, class_name: str) -> "type[WScalar] | None":
        for scalar in cls.all():
            if scalar.__name__ == class_name:
                return scalar
        return None

    @classmethod
    def is_scalar(cls, type_name: str) -> bool:
        return cls.by_type_name(type_name) is not None

    @classmethod
    def validate(cls, type_name: str, value: ScalarPayload | None) -> None:
        """None passes (unset semantics); otherwise exact python type match.
        Exactness keeps True out of Integer and 1 out of Boolean."""
        if value is None:
            return
        scalar = cls.by_type_name(type_name)
        if scalar is None:
            raise TypeError(f"{type_name!r} is not a scalar type")
        if type(value) is not scalar.PYTHON_TYPE:
            raise TypeError(
                f"{type_name} prop takes {scalar.PYTHON_TYPE.__name__}, got {type(value).__name__}"
            )
        scalar.check(value)

    @classmethod
    def check(cls, value: ScalarPayload) -> None:
        """Subclass invariant, enforced after the exact-type match.
        Base scalars carry no invariant beyond the type itself."""
        _ = value

    @classmethod
    def to_storage(cls, value: ScalarPayload) -> object:
        """Value -> column payload. Identity for the native column
        types; the year-less calendar types travel as text stamps."""
        return value

    @classmethod
    def from_storage(cls, raw: object) -> ScalarPayload:
        """Column payload -> value, the to_storage inverse."""
        return cast(ScalarPayload, raw)

    @classmethod
    @databasemethod(commit=True)
    def ensure_builtins(cls) -> None:
        from nylium.objects.wprop import WProp
        from nylium.objects.wtype import WType

        for scalar in cls.all():
            type_row = WType.ensure(scalar.TYPE_NAME, icon=scalar.ICON)
            _ = WProp.ensure(type_row, VALUE_PROP_KEY, type_row)


@final
class WString(WScalar):
    TYPE_NAME = "String"
    PYTHON_TYPE = str
    TABLE = StringValues
    ICON = "text_fields"


@final
class WInteger(WScalar):
    TYPE_NAME = "Integer"
    PYTHON_TYPE = int
    TABLE = IntegerValues
    ICON = "tag"


@final
class WNumeric(WScalar):
    TYPE_NAME = "Numeric"
    PYTHON_TYPE = Decimal
    TABLE = NumericValues
    ICON = "percent"


@final
class WBoolean(WScalar):
    TYPE_NAME = "Boolean"
    PYTHON_TYPE = bool
    TABLE = BooleanValues
    ICON = "toggle_on"


@final
class WDatetime(WScalar):
    TYPE_NAME = "Datetime"
    PYTHON_TYPE = datetime
    TABLE = DatetimeValues
    ICON = "calendar_clock"


@final
class WDate(WScalar):
    TYPE_NAME = "Date"
    PYTHON_TYPE = date
    TABLE = DateValues
    ICON = "calendar_month"


@final
class WTime(WScalar):
    TYPE_NAME = "Time"
    PYTHON_TYPE = time
    TABLE = TimeValues
    ICON = "schedule"


@final
class WColor(WScalar):
    """3-byte RGB hex ``#RRGGBB`` (ADR-0005): first-class scalar and the
    backing type of type/icon/tag colors. Stored in StringValues."""

    TYPE_NAME = "Color"
    PYTHON_TYPE = str
    TABLE = StringValues
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


@final
class WMonthDay(WScalar):
    """Month/day without a year, stored as its "MM-DD" stamp."""

    TYPE_NAME = "MonthDay"
    PYTHON_TYPE = MonthDay
    TABLE = MonthDayValues
    ICON = "calendar_today"

    @override
    @classmethod
    def to_storage(cls, value: ScalarPayload) -> object:
        return str(value)

    @override
    @classmethod
    def from_storage(cls, raw: object) -> ScalarPayload:
        return MonthDay.parse(str(raw))


@final
class WMonthDayTime(WScalar):
    """Month/day plus wall-clock time, stored as "MM-DDTHH:MM"."""

    TYPE_NAME = "MonthDayTime"
    PYTHON_TYPE = MonthDayTime
    TABLE = MonthDayTimeValues
    ICON = "alarm"

    @override
    @classmethod
    def to_storage(cls, value: ScalarPayload) -> object:
        return str(value)

    @override
    @classmethod
    def from_storage(cls, raw: object) -> ScalarPayload:
        return MonthDayTime.parse(str(raw))
