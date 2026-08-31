"""Scalar builtin types namespace.

Scalar types ("String", "Integer", ...) live in `types` like any other type
and get a canonical `value` prop, so props.value_type_uuid stays one honest
FK. This namespace owns the name -> values-table dispatch and the seeding.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from whiteout.database.tables import (
    BooleanValues,
    DatetimeValues,
    IntegerValues,
    NumericValues,
    StringValues,
)

VALUE_PROP_KEY = "value"


class scalars:
    TABLES: dict[str, type] = {
        "String": StringValues,
        "Integer": IntegerValues,
        "Numeric": NumericValues,
        "Boolean": BooleanValues,
        "Datetime": DatetimeValues,
    }
    PYTHON_TYPES: dict[type, str] = {
        str: "String",
        int: "Integer",
        Decimal: "Numeric",
        bool: "Boolean",
        datetime: "Datetime",
    }
    PYTHON_TYPE_NAMES: dict[str, str] = {
        py_type.__name__: name for py_type, name in PYTHON_TYPES.items()
    }

    @classmethod
    def is_scalar(cls, type_name: str) -> bool:
        return type_name in cls.TABLES

    @classmethod
    def table(cls, type_name: str) -> type:
        return cls.TABLES[type_name]

    @classmethod
    def name_for_python_type(cls, py_type: object) -> str | None:
        return cls.PYTHON_TYPES.get(py_type) if isinstance(py_type, type) else None

    @classmethod
    def name_for_python_type_name(cls, name: str) -> str | None:
        return cls.PYTHON_TYPE_NAMES.get(name)

    @classmethod
    def ensure_builtins(cls, session: Session) -> None:
        from whiteout.objects.wtype import WType

        for name in cls.TABLES:
            type_row = WType.ensure(session, name)
            type_row.ensure_prop(session, VALUE_PROP_KEY, type_row)
