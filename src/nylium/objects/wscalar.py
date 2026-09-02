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

from datetime import datetime
from decimal import Decimal
from typing import ClassVar, final

from sqlalchemy.orm import Session

from nylium.database import (
    Database,
    BooleanValues,
    DatetimeValues,
    IntegerValues,
    NumericValues,
    StringValues,
)

VALUE_PROP_KEY = "value"

ScalarPayload = str | int | Decimal | bool | datetime
ScalarTable = StringValues | IntegerValues | NumericValues | BooleanValues | DatetimeValues


class WScalar:
    TYPE_NAME: ClassVar[str]
    PYTHON_TYPE: ClassVar[type[ScalarPayload]]
    TABLE: ClassVar[type[ScalarTable]]

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

    @classmethod
    @Database.sessionmethod_begin
    def ensure_builtins(cls, _session: Session) -> None:
        from nylium.objects.wprop import WProp
        from nylium.objects.wtype import WType

        for scalar in cls.all():
            type_row = WType.ensure(scalar.TYPE_NAME)
            _ = WProp.ensure(type_row, VALUE_PROP_KEY, type_row)


@final
class WString(WScalar):
    TYPE_NAME = "String"
    PYTHON_TYPE = str
    TABLE = StringValues


@final
class WInteger(WScalar):
    TYPE_NAME = "Integer"
    PYTHON_TYPE = int
    TABLE = IntegerValues


@final
class WNumeric(WScalar):
    TYPE_NAME = "Numeric"
    PYTHON_TYPE = Decimal
    TABLE = NumericValues


@final
class WBoolean(WScalar):
    TYPE_NAME = "Boolean"
    PYTHON_TYPE = bool
    TABLE = BooleanValues


@final
class WDatetime(WScalar):
    TYPE_NAME = "Datetime"
    PYTHON_TYPE = datetime
    TABLE = DatetimeValues
