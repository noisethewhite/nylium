"""Shim over ``nylium.table_rows`` (ADR-0033).

``rows`` is a thin re-export shim; the real Row (mapped dataclass) + Table
store pairs live in ``table_rows``, one file per table.
"""
from nylium.table_rows import *  # noqa: F401,F403
