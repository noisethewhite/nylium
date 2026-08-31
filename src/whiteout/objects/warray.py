"""WArray: persistence of an array prop — an `Array<T>` instance plus
indexed `array_values` rows. Elements are boxed instances of the element
type, so scalars, links and nested arrays ride the same mechanism.

Boxes (instances of scalar or Array<...> types) are owned by their array:
rewriting or destroying the array destroys them recursively. Linked
WObjects of user types are never boxes and are never deleted here.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.tables import ArrayValues, Instances, InstanceValues
from whiteout.objects.wscalar import WScalar
from whiteout.objects.wtype import WType

if TYPE_CHECKING:
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
            raise TypeError(f"expected list, got {type(values).__name__}")
        array_uuid = cls._ensure_array_instance(session, owner_uuid, prop, elem_type)
        cls._fill(session, array_uuid, elem_type, values)

    @classmethod
    def destroy(cls, session: Session, array_uuid: UUID) -> None:
        """Delete the array instance and every box it owns, recursively."""
        cls._destroy_boxes(session, array_uuid)
        session.execute(
            sqla.delete(InstanceValues).where(InstanceValues.uuid == array_uuid)
        )
        instance = session.get(Instances, array_uuid)
        if instance is not None:
            session.delete(instance)

    # --- internals ---

    @classmethod
    def _fill(
        cls, session: Session, array_uuid: UUID, elem_type: str, values: list
    ) -> None:
        cls._destroy_boxes(session, array_uuid)
        for index, item in enumerate(values):
            session.add(
                ArrayValues(
                    inst_uuid=array_uuid,
                    index=index,
                    value_uuid=cls._box(session, elem_type, item),
                )
            )

    @classmethod
    def _destroy_boxes(cls, session: Session, array_uuid: UUID) -> None:
        box_uuids = list(
            session.scalars(
                sqla.select(ArrayValues.value_uuid).where(
                    ArrayValues.inst_uuid == array_uuid
                )
            ).all()
        )
        # detach pointer rows first: FK array_values.value_uuid -> instances
        # forbids deleting a box that is still referenced
        session.execute(
            sqla.delete(ArrayValues).where(ArrayValues.inst_uuid == array_uuid)
        )
        session.flush()
        for box_uuid in box_uuids:
            cls._destroy_box(session, box_uuid)

    @classmethod
    def _destroy_box(cls, session: Session, box_uuid: UUID) -> None:
        inst = session.get(Instances, box_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(session, inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {box_uuid} has dangling type")
        if WScalar.is_scalar(owner.name):
            session.delete(inst)  # its scalar values cascade on inst_uuid
            return
        if WType.is_array_name(owner.name):
            cls.destroy(session, box_uuid)
            return
        # user-type instance referenced from the array: not a box, keep it

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
        array_uuid = cls._create_array_instance(session, WType.array_name(elem_type))
        session.add(
            InstanceValues(uuid=array_uuid, prop_uuid=prop.uuid, inst_uuid=owner_uuid)
        )
        session.flush()
        return array_uuid

    @classmethod
    def _create_array_instance(cls, session: Session, array_type_name: str) -> UUID:
        array_uuid = uuid4()
        array_type = WType.ensure(session, array_type_name)
        session.add(
            Instances(uuid=array_uuid, type_uuid=array_type.uuid, name=ARRAY_INSTANCE_NAME)
        )
        session.flush()
        return array_uuid

    @classmethod
    def _unwrap(cls, session: Session, uuid: UUID, type_name: str):
        if WType.is_array_name(type_name):
            return cls.read(session, uuid, WType.element_name(type_name))
        scalar = WScalar.by_type_name(type_name)
        if scalar is None:
            from whiteout.objects.wobject import WObject

            return WObject.wrap(uuid)
        inst = session.get(Instances, uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = WType.by_uuid(session, inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        value_prop = owner.prop(session, "value")
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        row = session.get(scalar.TABLE, (uuid, value_prop.uuid))
        return None if row is None else row.value

    @classmethod
    def _box(cls, session: Session, type_name: str, value) -> UUID:
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(
                    f"{type_name} element takes list, got {type(value).__name__}"
                )
            array_uuid = cls._create_array_instance(session, type_name)
            cls._fill(session, array_uuid, WType.element_name(type_name), value)
            return array_uuid
        scalar = WScalar.by_type_name(type_name)
        if scalar is None:
            from whiteout.objects.wtypemeta import WTypeMeta

            WTypeMeta.check_link(session, type_name, value)
            return value._uuid
        WScalar.validate(type_name, value)
        box_uuid = uuid4()
        owner = WType.ensure(session, type_name)
        session.add(Instances(uuid=box_uuid, type_uuid=owner.uuid, name=str(value)))
        session.flush()
        value_prop = owner.prop(session, "value")
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        session.add(
            scalar.TABLE(inst_uuid=box_uuid, prop_uuid=value_prop.uuid, value=value)
        )
        return box_uuid
