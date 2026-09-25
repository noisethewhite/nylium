from __future__ import annotations
from typing import ClassVar
from nylium.database import Database
from nylium.ny.NyProp import NyProp
from nylium.ny.NyType import NyType
from typing import Protocol
from uuid import UUID
from typing import cast

from datetime import date, datetime, time
from decimal import Decimal

from nylium.data.types.MonthDay import MonthDay
from nylium.data.types.MonthDayTime import MonthDayTime
from nylium.data.rows import BooleanValue
from nylium.data.rows import DateValue
from nylium.data.rows import DatetimeValue
from nylium.data.rows import IntegerValue
from nylium.data.rows import MonthDayTimeValue
from nylium.data.rows import MonthDayValue
from nylium.data.rows import NumericValue
from nylium.data.rows import StringValue
from nylium.data.rows import TimeValue
from nylium.Constants import Constants


ScalarPayload = str | int | Decimal | bool | datetime | date | time | MonthDay | MonthDayTime
ScalarTable = (
    StringValue | IntegerValue | NumericValue | BooleanValue | DatetimeValue
    | DateValue | TimeValue | MonthDayValue | MonthDayTimeValue
)


class NyScalar:
    TYPE_NAME: ClassVar[str]
    PYTHON_TYPE: ClassVar[type[ScalarPayload]]
    TABLE: ClassVar[type[ScalarTable]]
    # The value-side cell store (nylium.data.tables.values) backing this marker
    SCALAR: ClassVar[type[_ScalarStore]]
    # Material Symbols name, rendered gray and immutable for builtins
    ICON: ClassVar[str]

    @classmethod
    def all(cls) -> "list[type[NyScalar]]":
        return cls.__subclasses__()

    @classmethod
    def by_type_name(cls, type_name: str) -> "type[NyScalar] | None":
        for scalar in cls.all():
            if scalar.TYPE_NAME == type_name:
                return scalar
        return None

    @classmethod
    def by_class_name(cls, class_name: str) -> "type[NyScalar] | None":
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
    @Database.commit_after_this
    def ensure_builtins(cls) -> None:

        for scalar in cls.all():
            type_row = NyType.ensure(scalar.TYPE_NAME, icon=scalar.ICON)
            _ = NyProp.ensure(type_row, Constants.Props.VALUE_PROP_KEY, type_row)


class _ScalarStore(Protocol):
    """The value-side store shape a scalar marker binds to (ADR-0031)."""

    @classmethod
    def read(cls, inst_uuid: UUID, prop_uuid: UUID) -> object: ...
    @classmethod
    def write(cls, inst_uuid: UUID, prop_uuid: UUID, value: object) -> None: ...
    @classmethod
    def clear(cls, inst_uuid: UUID, prop_uuid: UUID) -> bool: ...
