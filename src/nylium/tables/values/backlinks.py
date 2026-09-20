# Backlink read-side projection (ADR-0020): who points at a given
# instance — via direct link props (instance_values) and via array
# membership (array_values → the array box's owner link). Nothing is
# stored; the reverse edge set is recomputed on every read, mirroring
# the ADR-0005 tag projection. Statement lives here (ADR-0019), the
# ObjectView assembly stays in the api layer.
from typing import cast
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy.orm import aliased

from nylium.database import Database
from nylium.tables.values.array_values import TABLE_ArrayValues
from nylium.tables.values.instance_values import TABLE_InstanceValues


@Database.use_same_session
def backlink_refs(target_uuid: UUID) -> list[tuple[UUID, str]]:
    """(owner uuid, owner type name) for every instance that points at
    ``target_uuid`` — directly through a link prop or through membership
    in one of its arrays. Owners deduplicated, direct links first.

    Table classes are imported lazily so this module stays cycle-free at
    load time (mirrors ``array_values.array_tag_rows``).
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
