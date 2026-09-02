"""WArray: persistence of an array prop — an `Array<T>` instance plus
indexed `array_values` rows. Elements are boxed instances of the element
type, so scalars, links and nested arrays ride the same mechanism.

Boxes (instances of scalar or Array<...> types) are owned by their array:
rewriting or destroying the array destroys them recursively. Linked
WObjects of user types are never boxes and are never deleted here.

Never imports wobject: link wrapping goes through WTypeMeta.root()
and link values are narrowed to the WObjectShape protocol. That's what
keeps the objects package acyclic.
"""
from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database, ArrayValues, Instances, InstanceValues
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import VALUE_PROP_KEY, ScalarPayload, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WObjectShape, WTypeMeta

ARRAY_INSTANCE_NAME = "array"


class WArray:
    @classmethod
    @Database.sessionmethod.no_commit
    def read(cls, session: Session, array_uuid: UUID, elem_type: str) -> list[StoredValue]:
        rows = session.scalars(
            sqla.select(ArrayValues)
            .where(ArrayValues.inst_uuid == array_uuid)
            .order_by(ArrayValues.index)
        ).all()
        return [cls._unwrap(row.value_uuid, elem_type) for row in rows]

    @classmethod
    @Database.sessionmethod.bundled_with_commit
    def write(
        cls,
        owner_uuid: UUID,
        prop: WProp,
        elem_type: str,
        values: list[StoredValue],
    ) -> None:
        array_uuid = cls._ensure_array_instance(owner_uuid, prop, elem_type)
        cls._fill(array_uuid, elem_type, values)

    @classmethod
    @Database.sessionmethod.with_commit
    def destroy(cls, session: Session, array_uuid: UUID) -> None:
        """Delete the array instance and every box it owns, recursively."""
        cls._destroy_boxes(array_uuid)
        _ = session.execute(
            sqla.delete(InstanceValues).where(InstanceValues.uuid == array_uuid)
        )
        instance = session.get(Instances, array_uuid)
        if instance is not None:
            session.delete(instance)

    # --- internals ---

    @classmethod
    @Database.sessionmethod.with_commit
    def _fill(
        cls, session: Session, array_uuid: UUID, elem_type: str, values: list[StoredValue]
    ) -> None:
        cls._destroy_boxes(array_uuid)
        for index, item in enumerate(values):
            session.add(
                ArrayValues(
                    inst_uuid=array_uuid,
                    index=index,
                    value_uuid=cls._box(elem_type, item),
                )
            )

    @classmethod
    @Database.sessionmethod.with_commit
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
        _ = session.execute(
            sqla.delete(ArrayValues).where(ArrayValues.inst_uuid == array_uuid)
        )
        session.flush()
        for box_uuid in box_uuids:
            cls._destroy_box(box_uuid)

    @classmethod
    @Database.sessionmethod.with_commit
    def _destroy_box(cls, session: Session, box_uuid: UUID) -> None:
        inst = session.get(Instances, box_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {box_uuid} has dangling type")
        if WScalar.is_scalar(owner.name):
            session.delete(inst)  # its scalar values cascade on inst_uuid
            return
        if WType.is_array_name(owner.name):
            cls.destroy(box_uuid)
            return
        # user-type instance referenced from the array: not a box, keep it

    @classmethod
    @Database.sessionmethod.with_commit
    def _ensure_array_instance(
        cls, session: Session, owner_uuid: UUID, prop: WProp, elem_type: str
    ) -> UUID:
        link = session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == owner_uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )
        if link is not None:
            return link.uuid
        array_uuid = cls._create_array_instance(WType.array_name(elem_type))
        session.add(
            InstanceValues(uuid=array_uuid, prop_uuid=prop.uuid, inst_uuid=owner_uuid)
        )
        session.flush()
        return array_uuid

    @classmethod
    @Database.sessionmethod.with_commit
    def _create_array_instance(cls, session: Session, array_type_name: str) -> UUID:
        array_uuid = uuid4()
        array_type = WType.ensure(array_type_name)
        session.add(
            Instances(uuid=array_uuid, type_uuid=array_type.uuid, name=ARRAY_INSTANCE_NAME)
        )
        session.flush()
        return array_uuid

    @classmethod
    @Database.sessionmethod.no_commit
    def _unwrap(cls, session: Session, uuid: UUID, type_name: str) -> StoredValue:
        if WType.is_array_name(type_name):
            return cls.read(uuid, WType.element_name(type_name))
        scalar = WScalar.by_type_name(type_name)
        if scalar is None:
            return WTypeMeta.root().wrap(uuid)
        inst = session.get(Instances, uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        value_prop = WProp.by_key(owner, VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        row = session.get(scalar.TABLE, (uuid, value_prop.uuid))
        return None if row is None else row.value

    @classmethod
    @Database.sessionmethod.with_commit
    def _box(cls, session: Session, type_name: str, value: StoredValue) -> UUID:
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(
                    f"{type_name} element takes list, got {type(value).__name__}"
                )
            array_uuid = cls._create_array_instance(type_name)
            cls._fill(array_uuid, WType.element_name(type_name), value)
            return array_uuid
        scalar = WScalar.by_type_name(type_name)
        if scalar is None:
            WTypeMeta.check_link(type_name, value)
            return cast(WObjectShape, value).uuid
        WScalar.validate(type_name, cast(ScalarPayload | None, value))
        box_uuid = uuid4()
        owner = WType.ensure(type_name)
        session.add(Instances(uuid=box_uuid, type_uuid=owner.uuid, name=str(value)))
        session.flush()
        value_prop = WProp.by_key(owner, VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        session.add(
            scalar.TABLE(inst_uuid=box_uuid, prop_uuid=value_prop.uuid, value=value)
        )
        return box_uuid
