"""Quantity: the python-level value of a `Numeric<Unit>` prop.

A magnitude plus the unit part name it was entered in (`None` = the
unit's base part). Frozen and dependency-free so every layer — object,
api, codec — can share it without import cycles.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str | None = None
