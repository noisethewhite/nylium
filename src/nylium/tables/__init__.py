"""Shim over ``nylium.table_rows`` (ADR-0033).

``tables`` and ``rows`` are now thin re-export shims; the real Row (mapped
dataclass) + Table store pairs live in ``table_rows``, one file per table.
``base`` still holds ``reg`` and the mapped-dataclass decorator.
"""
from nylium.tables.base import reg as reg
from nylium.table_rows import *  # noqa: F401,F403
