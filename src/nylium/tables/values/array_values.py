# Array elements: the array itself is an instance (of an array type);
# rows map (array instance, index) -> element. The element is either a box
# instance (scalar/nested-array), a referenced user-type instance, or — for
# Array<File/Document/Image> (ADR-0008) — a files.uuid. So value_uuid is a
# bare uuid, not an FK: files aren't instances and would violate the
# instances FK. Cleanup is manual in WArray, not DB-cascaded.
# Statement helpers live here too (ADR-0019).
from typing import ClassVar, cast
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, use_same_session
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_ArrayValues:
    __tablename__: ClassVar[str] = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(nullable=False)


@use_same_session
def delete_memberships(value_uuid: UUID) -> None:
    """Drop every array-membership row pointing at the given element uuid."""
    _ = Database.execute(
        sqla.delete(TABLE_ArrayValues).where(TABLE_ArrayValues.value_uuid == value_uuid)
    )


@use_same_session
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


@use_same_session
def add_element(array_uuid: UUID, index: int, value_uuid: UUID) -> None:
    """Append one element row (plain insert — _fill rewrites from empty)."""
    Database.add(
        TABLE_ArrayValues(inst_uuid=array_uuid, index=index, value_uuid=value_uuid)
    )


@use_same_session
def delete_elements_of(array_uuid: UUID) -> None:
    """Detach every element row of the array and flush — the FK
    array_values.value_uuid -> instances forbids deleting a box that is
    still referenced, so the pointer rows go first."""
    _ = Database.execute(
        sqla.delete(TABLE_ArrayValues).where(TABLE_ArrayValues.inst_uuid == array_uuid)
    )
    Database.flush()


@use_same_session
def array_tag_rows(
    element_uuid: UUID, array_type_name: str, name_prop_key: str
) -> list[tuple[UUID, str, str, str | None, str]]:
    """ADR-0005 reverse projection: every array that holds ``element_uuid``
    as a member of an ``Array<array_type_name>`` prop, with enough info to
    paint a tag chip — (owner uuid, prop key, registry name, display name,
    owner type color). One query, no N+1.

    Table classes are imported lazily so this module stays cycle-free at
    load time (mirrors ``instance_values.array_link_uuids_of``).
    """
    from sqlalchemy.orm import aliased

    from nylium.tables.decor.table_type_decor import TABLE_TypeDecor
    from nylium.objects.tables.table_instances import TABLE_Instances
    from nylium.objects.tables.table_props import TABLE_Props
    from nylium.objects.tables.table_types import TABLE_Types
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
