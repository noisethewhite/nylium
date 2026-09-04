"""Wire DTOs -> Api input, guided by the declared type schema.

The wire shape alone is ambiguous: a JSON string can be a String, an
ISO Datetime or a Decimal. The prop's declared value type decides
which coercion applies — that's why decoding needs the schema.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import cast

from nylium.api.api import Api, PropInput
from nylium.api.views import ArrayValue, PropValue, RefValue, ScalarValue
from nylium.objects.monthday import MonthDay, MonthDayTime
from nylium.objects.quantity import Quantity
from nylium.objects.wenum import WEnum
from nylium.objects.wscalar import (
    ScalarPayload,
    WBoolean,
    WDate,
    WDatetime,
    WInteger,
    WMonthDay,
    WMonthDayTime,
    WNumeric,
    WScalar,
    WString,
    WTime,
)
from nylium.objects.wtype import WType


class PropCodec:
    """Turns JSON-shaped PropValue DTOs into the PropInput the Api
    facade understands. Pure functions of (value, declared type)."""

    @classmethod
    def decode(cls, type_name: str, props: dict[str, PropValue]) -> dict[str, PropInput]:
        type_view = Api.get_type(type_name)
        if type_view is None:
            raise KeyError(f"no type {type_name!r}")
        schema = {prop.key: prop.value_type for prop in type_view.props}
        return {
            key: cls._decode_value(value, cls._schema_type(schema, type_name, key))
            for key, value in props.items()
        }

    @classmethod
    def _schema_type(cls, schema: dict[str, str], type_name: str, key: str) -> str:
        value_type = schema.get(key)
        if value_type is None:
            raise KeyError(f"type {type_name!r} has no prop {key!r}")
        return value_type

    @classmethod
    def _decode_value(cls, value: PropValue, type_name: str) -> PropInput:
        if WScalar.by_type_name(type_name) is not None:
            if not isinstance(value, ScalarValue):
                raise TypeError(cls._shape_error(type_name, "ScalarValue", value))
            return cls._coerce_scalar(value.value, type_name)
        if WType.unit_param_of(type_name) is not None:
            if not isinstance(value, ScalarValue):
                raise TypeError(cls._shape_error(type_name, "ScalarValue", value))
            if value.value is None:
                return None
            coerced = cls._coerce_scalar(value.value, WNumeric.TYPE_NAME)
            unit = value.unit
            if unit is not None and type(unit) is not str:
                raise TypeError(f"unit {unit!r} is not a valid {type_name}")
            # part membership and conversion happen in WUnit.validate,
            # when the write hits the object layer
            return Quantity(value=cast(Decimal, coerced), unit=unit)
        if WEnum.is_enum(type_name):
            if not isinstance(value, ScalarValue):
                raise TypeError(cls._shape_error(type_name, "ScalarValue", value))
            raw = value.value
            if raw is not None and type(raw) is not str:
                raise TypeError(f"value {raw!r} is not a valid {type_name}")
            return raw
        if WType.is_array_name(type_name):
            if not isinstance(value, ArrayValue):
                raise TypeError(cls._shape_error(type_name, "ArrayValue", value))
            if value.items is None:
                raise TypeError(
                    "unsetting arrays is not supported — omit the prop (untouched) or send an empty list"
                )
            element_name = WType.element_name(type_name)
            return [cls._decode_value(item, element_name) for item in value.items]
        if not isinstance(value, RefValue):
            raise TypeError(cls._shape_error(type_name, "RefValue", value))
        return value.ref

    @classmethod
    def _coerce_scalar(cls, raw: ScalarPayload | None, type_name: str) -> ScalarPayload | None:
        if raw is None:
            return None
        scalar = WScalar.by_type_name(type_name)
        if scalar is WString and type(raw) is str:
            return raw
        if scalar is WInteger and type(raw) is int:
            return raw
        if scalar is WBoolean and type(raw) is bool:
            return raw
        if scalar is WNumeric and type(raw) in (int, float, Decimal):
            # str() detour: Decimal(float) would bake in binary float noise
            return Decimal(str(raw))
        if scalar is WNumeric and type(raw) is str:
            try:
                return Decimal(raw)
            except InvalidOperation:
                raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        if scalar is WDatetime:
            if isinstance(raw, datetime):
                return raw
            if type(raw) is str:
                try:
                    return datetime.fromisoformat(raw)
                except ValueError:
                    raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        if scalar is WDate:
            if type(raw) is date:
                return raw
            if type(raw) is str:
                try:
                    return date.fromisoformat(raw)
                except ValueError:
                    raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        if scalar is WTime:
            if type(raw) is time:
                return raw
            if type(raw) is str:
                try:
                    return time.fromisoformat(raw)
                except ValueError:
                    raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        if scalar is WMonthDay:
            if type(raw) is MonthDay:
                return raw
            if type(raw) is str:
                try:
                    return MonthDay.parse(raw)
                except ValueError:
                    raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        if scalar is WMonthDayTime:
            if type(raw) is MonthDayTime:
                return raw
            if type(raw) is str:
                try:
                    return MonthDayTime.parse(raw)
                except ValueError:
                    raise TypeError(f"value {raw!r} is not a valid {type_name}") from None
        raise TypeError(f"value {raw!r} is not a valid {type_name}")

    @classmethod
    def _shape_error(cls, type_name: str, expected: str, value: PropValue) -> str:
        return (
            f"prop of type {type_name!r} takes {expected}, "
            f"got {type(value).__name__}"
        )
