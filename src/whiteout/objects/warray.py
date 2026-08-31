"""WArray: persistence of an array prop — an `Array<T>` instance plus
indexed `array_values` rows. Elements are boxed instances of the element
type, so scalars and links ride the same mechanism."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.tables import ArrayValues, Instances, InstanceValues
from whiteout.objects.scalars import VALUE_PROP_KEY, scalars
from whiteout.objects.wtype import WType

if TYPE_CHECKING:
    from whiteout.objects.wobject import WObject
    from whiteout.objects.wprop import WProp

ARRAY_INSTANCE_NAME = "array"


class WArray:
    @classmethod
    def read(cls, session: Session, array_uuid: UUID, elem_type: str) -> list:
        rows = session.scalars(
            sqla.select(ArrayValues)
            .where(ArrayValues.inst_uuid == array_uuid)
            .order_by(ArrayValues.index)
        ).all()
        return [cls._unwrap(session, row.value_uuid, elem_type) for row in rows]

    @classmethod
    def write(
        cls,
        session: Session,
        owner_uuid: UUID,
        prop: "WProp",
        elem_type: str,
        values: list,
    ) -> None:
        if not isinstance(values, list):
            raise TypeError(f"expected list, got {type(values)}")
        array_uuid = cls._ensure_array_instance(session, owner_uuid, prop, elem_type)
        session.execute(
            sqla.delete(ArrayValues).where(ArrayValues.inst_uuid == array_uuid)
        )
        for index, item in enumerate(values):
            session.add(
                ArrayValues(
                    inst_uuid=array_uuid,
                    index=index,
                    value_uuid=cls._box(session, elem_type, item),
                )
            )

    @classmethod
    def _ensure_array_instance(
        cls, session: Session, owner_uuid: UUID, prop: "WProp", elem_type: str
    ) -> UUID:
        link = session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == owner_uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )
        if link is not None:
            return link.uuid
        array_uuid = uuid4()
        array_type = WType.ensure(session, WType.array_name(elem_type))
        session.add(
            Instances(uuid=array_uuid, type_uuid=array_type.uuid, name=ARRAY_INSTANCE_NAME)
        )
        session.flush()
        session.add(
            InstanceValues(uuid=array_uuid, prop_uuid=prop.uuid, inst_uuid=owner_uuid)
        )
        return array_uuid

    @classmethod
    def _unwrap(cls, session: Session, uuid: UUID, type_name: str):
        if not scalars.is_scalar(type_name):
            from whiteout.objects.wobject import WObject

            return WObject.wrap(uuid)
        inst = session.get(Instances, uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = WType.by_uuid(session, inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        value_prop = owner.prop(session, VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its {VALUE_PROP_KEY!r} prop")
        row = session.get(scalars.table(type_name), (uuid, value_prop.uuid))
        return None if row is None else row.value

    @classmethod
    def _box(cls, session: Session, type_name: str, value) -> UUID:
        from whiteout.objects.wobject import WObject

        if isinstance(value, WObject):
            return value._uuid
        box_uuid = uuid4()
        owner = WType.ensure(session, type_name)
        session.add(Instances(uuid=box_uuid, type_uuid=owner.uuid, name=str(value)))
        session.flush()
        if scalars.is_scalar(type_name):
            value_prop = owner.prop(session, VALUE_PROP_KEY)
            if value_prop is None:
                raise RuntimeError(
                    f"scalar type {type_name} lost its {VALUE_PROP_KEY!r} prop"
                )
            session.add(
                scalars.table(type_name)(
                    inst_uuid=box_uuid, prop_uuid=value_prop.uuid, value=value
                )
            )
        return box_uuid
