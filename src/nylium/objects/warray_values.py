"""Array statement helpers (ADR-0019): SQL over ``array_values`` rows, the
array-tag reverse projection (ADR-0005) and the collect range lookup
(ADR-0025).

Moved here from ``tables/values/array_values.py`` and
``tables/values/collect_range.py`` in ADR-0030 phase C. Kept out of
``warray.py`` so ``wembedded`` can import ``element_uuids_of`` without a
``warray <-> wembedded`` import cycle.
"""
from __future__ import annotations

from typing import cast
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.tables.values.array_values import TABLE_ArrayValues


@Database.use_same_session
def delete_memberships(value_uuid: UUID) -> None:
    """Drop every array-membership row pointing at the given element uuid."""
    _ = Database.execute(
        sqla.delete(TABLE_ArrayValues).where(TABLE_ArrayValues.value_uuid == value_uuid)
    )


@Database.use_same_session
def element_uuids_of(array_uuid: UUID) -> list[UUID]:
    """Element uuids of one array, in index order (WArray.read relies on
    the ordering; the destroy path just wants the snapshot)."""
    return list(
        Database.scalars(
            sqla.select(TABLE_ArrayValues.value_uuid)
            .where(TABLE_ArrayValues.inst_uuid == array_uuid)
            .order_by(TABLE_ArrayValues.index)
        ).all()
    )


@Database.use_same_session
def add_element(array_uuid: UUID, index: int, value_uuid: UUID) -> None:
    """Append one element row (plain insert — _fill rewrites from empty)."""
    Database.add(
        TABLE_ArrayValues(inst_uuid=array_uuid, index=index, value_uuid=value_uuid)
    )


@Database.use_same_session
def delete_elements_of(array_uuid: UUID) -> None:
    """Detach every element row of the array and flush — the FK
    array_values.value_uuid -> instances forbids deleting a box that is
    still referenced, so the pointer rows go first."""
    _ = Database.execute(
        sqla.delete(TABLE_ArrayValues).where(TABLE_ArrayValues.inst_uuid == array_uuid)
    )
    Database.flush()


@Database.use_same_session
def array_tag_rows(
    element_uuid: UUID, array_type_name: str, name_prop_key: str
) -> list[tuple[UUID, str, str, str | None, str]]:
    """ADR-0005 reverse projection: every array that holds ``element_uuid``
    as a member of an ``Array<array_type_name>`` prop, with enough info to
    paint a tag chip — (owner uuid, prop key, registry name, display name,
    owner type color). One query, no N+1.

    Table classes are imported lazily so this module stays cycle-free at
    load time (mirrors ``wlink.array_link_uuids_of``).
    """
    from sqlalchemy.orm import aliased

    from nylium.tables.decor.table_type_decor import TABLE_TypeDecor
    from nylium.tables.objects.table_instances import TABLE_Instances
    from nylium.tables.objects.table_props import TABLE_Props
    from nylium.tables.objects.table_types import TABLE_Types
    from nylium.tables.values.instance_values import TABLE_InstanceValues
    from nylium.tables.values.string_values import TABLE_StringValues

    name_prop = aliased(TABLE_Props)
    owner_types = aliased(TABLE_Types)
    owner_decor = aliased(TABLE_TypeDecor)
    rows = Database.execute(
        sqla.select(
            TABLE_InstanceValues.inst_uuid,
            TABLE_Props.key,
            TABLE_Instances.name,
            TABLE_StringValues.value,
            owner_decor.color,
        )
        .select_from(TABLE_ArrayValues)
        .join(TABLE_InstanceValues, TABLE_InstanceValues.uuid == TABLE_ArrayValues.inst_uuid)
        .join(TABLE_Props, TABLE_Props.uuid == TABLE_InstanceValues.prop_uuid)
        .join(TABLE_Types, TABLE_Types.uuid == TABLE_Props.value_type_uuid)
        .join(TABLE_Instances, TABLE_Instances.uuid == TABLE_InstanceValues.inst_uuid)
        .join(owner_types, owner_types.uuid == TABLE_Instances.type_uuid)
        .join(owner_decor, owner_decor.uuid == owner_types.uuid)
        .join(name_prop, name_prop.owner_type_uuid == TABLE_Instances.type_uuid)
        .join(
            TABLE_StringValues,
            sqla.and_(
                TABLE_StringValues.inst_uuid == TABLE_Instances.uuid,
                TABLE_StringValues.prop_uuid == name_prop.uuid,
            ),
            isouter=True,
        )
        .where(
            TABLE_ArrayValues.value_uuid == element_uuid,
            TABLE_Types.name == array_type_name,
            name_prop.key == name_prop_key,
        )
        .distinct()
    ).all()
    return [
        (cast(UUID, r[0]), cast(str, r[1]), cast(str, r[2]), cast("str | None", r[3]), cast(str, r[4]))
        for r in rows
    ]


@Database.use_same_session
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
