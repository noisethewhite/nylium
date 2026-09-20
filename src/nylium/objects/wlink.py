"""Link-statement helpers (ADR-0019 / ADR-0030 phase C): the statements
that read and write ``instance_values`` link rows (link props, embedded
children, array-instance links) and the ADR-0020 backlink projection.

Moved verbatim from ``tables/values/instance_values.py`` and
``tables/values/backlinks.py`` — only the import paths changed. The
``TABLE_InstanceValues`` / ``TABLE_ArrayValues`` classes stay in the
table layer; this module imports them (objects may import tables).
"""
from typing import cast
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy.orm import aliased

from nylium.database import Database
from nylium.tables.values.array_values import TABLE_ArrayValues
from nylium.tables.values.instance_values import TABLE_InstanceValues


@Database.use_same_session
def link_for(inst_uuid: UUID, prop_uuid: UUID) -> TABLE_InstanceValues | None:
    """The link row held by (owner instance, prop), or None."""
    return Database.scalar(
        sqla.select(TABLE_InstanceValues).where(
            TABLE_InstanceValues.inst_uuid == inst_uuid,
            TABLE_InstanceValues.prop_uuid == prop_uuid,
        )
    )


@Database.use_same_session
def merge_link(uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
    """Insert-or-replace the link row for (owner, prop) — the composite
    pk — pointing at the given target uuid (ADR-0028)."""
    _ = Database.merge(
        TABLE_InstanceValues(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid)
    )


@Database.use_same_session
def delete_row(row: TABLE_InstanceValues) -> None:
    """Delete the given link row (already fetched by the caller)."""
    Database.delete(row)


@Database.use_same_session
def delete_links_to(uuid: UUID) -> None:
    """Delete every link row whose target is the given instance uuid."""
    _ = Database.execute(
        sqla.delete(TABLE_InstanceValues).where(TABLE_InstanceValues.uuid == uuid)
    )


@Database.use_same_session
def linked_uuids_of(prop_uuid: UUID) -> list[UUID]:
    """Uuids of every instance linked through the given prop, across all
    owners — the sweep list before an embedded prop is deleted or retyped."""
    return list(
        Database.scalars(
            sqla.select(TABLE_InstanceValues.uuid).where(
                TABLE_InstanceValues.prop_uuid == prop_uuid
            )
        ).all()
    )


@Database.use_same_session
def add_link(uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
    """Insert a brand-new link row and flush — the embedded child is a fresh
    uuid4, so this must stay a plain insert (merge would mask a uuid
    collision instead of failing on it). The flush pins insert order:
    instance_values.uuid FKs into instances."""
    Database.add(
        TABLE_InstanceValues(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid)
    )
    Database.flush()


@Database.use_same_session
def array_link_uuids_of(owner_inst_uuid: UUID) -> list[UUID]:
    """Uuids of array-instance links held by the given owner."""
    from nylium.tables.objects.table_props import TABLE_Props
    from nylium.tables.objects.table_types import TABLE_Types

    stmt = (
        sqla.select(TABLE_InstanceValues.uuid)
        .join(TABLE_Props, TABLE_InstanceValues.prop_uuid == TABLE_Props.uuid)
        .join(TABLE_Types, TABLE_Props.value_type_uuid == TABLE_Types.uuid)
        .where(
            TABLE_InstanceValues.inst_uuid == owner_inst_uuid,
            # mirrors WType.ARRAY_TYPE_PREFIX (objects layer imports tables,
            # so the constant cannot flow the other way)
            TABLE_Types.name.like("Array<%"),
        )
    )
    return list(Database.scalars(stmt).all())


@Database.use_same_session
def backlink_refs(target_uuid: UUID) -> list[tuple[UUID, str]]:
    """(owner uuid, owner type name) for every instance that points at
    ``target_uuid`` — directly through a link prop or through membership
    in one of its arrays. Owners deduplicated, direct links first.

    Table classes are imported lazily so this module stays cycle-free at
    load time (mirrors ``warray.array_tag_rows``).
    """
    from nylium.tables.objects.table_instances import TABLE_Instances
    from nylium.tables.objects.table_types import TABLE_Types

    direct_types = aliased(TABLE_Types)
    direct = Database.execute(
        sqla.select(TABLE_InstanceValues.inst_uuid, direct_types.name)
        .join(
            TABLE_Instances,
            TABLE_InstanceValues.inst_uuid == TABLE_Instances.uuid,
        )
        .join(direct_types, TABLE_Instances.type_uuid == direct_types.uuid)
        .where(TABLE_InstanceValues.uuid == target_uuid)
    ).all()

    box_link = aliased(TABLE_InstanceValues)
    array_types = aliased(TABLE_Types)
    via_arrays = Database.execute(
        sqla.select(box_link.inst_uuid, array_types.name)
        .select_from(TABLE_ArrayValues)
        # the array box itself is linked from its owner by instance_values
        .join(box_link, TABLE_ArrayValues.inst_uuid == box_link.uuid)
        .join(TABLE_Instances, box_link.inst_uuid == TABLE_Instances.uuid)
        .join(array_types, TABLE_Instances.type_uuid == array_types.uuid)
        .where(TABLE_ArrayValues.value_uuid == target_uuid)
    ).all()

    seen: set[UUID] = set()
    refs: list[tuple[UUID, str]] = []
    for r in [*direct, *via_arrays]:
        owner_uuid = cast(UUID, r[0])
        if owner_uuid in seen:
            continue
        seen.add(owner_uuid)
        refs.append((owner_uuid, cast(str, r[1])))
    # deterministic wire order: SQL row order is an implementation detail
    return sorted(refs, key=lambda item: (item[1], str(item[0])))
