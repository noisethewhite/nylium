"""ADR-0025: range lookup of instance uuids by an ordered scalar prop's value.

A collect prop derives its array at read time with one reverse query over the
member prop's value table, bounded by the owner's `from`/`to` siblings.
"""
from __future__ import annotations

from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, databasemethod


@databasemethod(commit=False)
def collect_range(
    prop_uuid: UUID, spec_name: str, lo: object, hi: object
) -> list[UUID]:
    """Every instance whose `prop_uuid` value falls within [lo, hi] inclusive.

    `spec_name` is the member prop's value spec (ordered scalar); the matching
    value table and comparison type are resolved lazily to keep this leaf out
    of the objects-layer import cycle.
    """
    # lazy imports: wscalar pulls in wprop, which pulls in tables.objects.props,
    # which pulls in the value tables — importing at module level would cycle.
    from nylium.objects.wscalar import WDate, WDatetime, WInteger
    from nylium.tables.values.date_values import TABLE_DateValues
    from nylium.tables.values.datetime_values import TABLE_DatetimeValues
    from nylium.tables.values.integer_values import TABLE_IntegerValues
    from nylium.tables.values.numeric_values import TABLE_NumericValues

    if spec_name == WInteger.TYPE_NAME:
        table = TABLE_IntegerValues
    elif spec_name == WDate.TYPE_NAME:
        table = TABLE_DateValues
    elif spec_name == WDatetime.TYPE_NAME:
        table = TABLE_DatetimeValues
    else:
        # Numeric and Numeric<Unit> both store their magnitude in numeric_values
        table = TABLE_NumericValues
    return list(
        Database.scalars(
            sqla.select(table.inst_uuid).where(
                table.prop_uuid == prop_uuid,
                table.value >= lo,
                table.value <= hi,
            )
        ).all()
    )
