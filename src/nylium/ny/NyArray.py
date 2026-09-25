"""NyArray: persistence of an array prop — an `Array<T>` instance plus
indexed `array_values` rows. Elements are boxed instances of the element
type, so scalars, links and nested arrays ride the same mechanism.

Boxes (instances of scalar or Array<...> types) are owned by their array:
rewriting or destroying the array destroys them recursively. Linked
NyObjects of user types are never boxes and are never deleted here.

Never imports nyobject: link wrapping goes through NyTypeMeta.root()
and link values are narrowed to the NyObjectShape protocol. That's what
keeps the objects package acyclic.
"""
from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from nylium.database import Database
from nylium.data.tables import files
from nylium.data.tables import Instances, instances
from nylium.data.tables import ArrayValues
from nylium.data.tables import InstanceValues
from nylium.ny.NyEnum import NyEnum
from nylium.ny.NyEmbedded import NyEmbedded
from nylium.ny.NyFile import NyFile
from nylium.ny.NyProp import NyProp
from nylium.ny.NyScalar import NyScalar, ScalarPayload
from nylium.ny.NyString import NyString
from nylium.Constants import Constants
from nylium.ny.NyType import NyType
from nylium.ny.NyObjectShape import NyObjectShape
from nylium.ny.NyTypeMeta import StoredValue, NyTypeMeta
from nylium.uuid import ObjectUUID, TypeUUID
from nylium.uuid.objects import ArrayUUID



class NyArray:
    @classmethod
    @Database.use_same_session
    def read(cls, array_uuid: ArrayUUID, elem_type: str) -> list[StoredValue]:
        return [cls._unwrap(uuid, elem_type) for uuid in ArrayValues.element_uuids_of(array_uuid)]

    @classmethod
    @Database.commit_after_this
    def write(
        cls,
        owner_uuid: ObjectUUID,
        prop: NyProp,
        elem_type: str,
        values: list[StoredValue] | None,
    ) -> None:
        if values is None:
            # None unsets the prop: destroy the array instance (and its boxes)
            link = InstanceValues.link_for(owner_uuid, prop.uuid)
            if link is not None:
                cls.destroy(ArrayUUID.of(link.uuid))
            return
        array_uuid = cls._ensure_array_instance(owner_uuid, prop, elem_type)
        cls._fill(array_uuid, elem_type, values, owner_uuid, prop)

    @classmethod
    @Database.commit_after_this
    def destroy(cls, array_uuid: ArrayUUID) -> None:
        """Delete the array instance and every box it owns, recursively."""
        cls._destroy_boxes(array_uuid)
        InstanceValues.delete_links_to(array_uuid)
        Instances.delete_row(array_uuid)

    # --- internals ---

    @classmethod
    @Database.commit_after_this
    def _fill(
        cls,
        array_uuid: ArrayUUID,
        elem_type: str,
        values: list[StoredValue],
        owner_uuid: ObjectUUID,
        prop: NyProp,
    ) -> None:
        cls._destroy_boxes(array_uuid)
        for index, item in enumerate(values):
            ArrayValues.add_element(
                array_uuid, index, cls._box(elem_type, item, array_uuid, owner_uuid, prop, index)
            )

    @classmethod
    @Database.commit_after_this
    def _destroy_boxes(cls, array_uuid: ArrayUUID) -> None:
        box_uuids = ArrayValues.element_uuids_of(array_uuid)
        # detach pointer rows first: FK array_values.value_uuid -> instances
        # forbids deleting a box that is still referenced
        ArrayValues.delete_elements_of(array_uuid)
        for box_uuid in box_uuids:
            cls._destroy_box(ObjectUUID.of(box_uuid))

    @classmethod
    @Database.commit_after_this
    def _destroy_box(cls, box_uuid: ObjectUUID) -> None:
        inst = instances.get(box_uuid)
        if inst is None:
            return
        owner = NyType.by_uuid(TypeUUID.of(inst.type_uuid))
        if owner is None:
            raise RuntimeError(f"instance {box_uuid} has dangling type")
        if NyScalar.is_scalar(owner.name):
            Instances.delete_row(box_uuid)  # its scalar values cascade on inst_uuid
            return
        if NyType.is_array_name(owner.name):
            cls.destroy(ArrayUUID.of(box_uuid))
            return
        if owner.is_embedded:
            # ADR-0021: an Array<Embedded> element is a composition child —
            # its lifecycle is owned by the array, so a rewrite/delete of
            # the array deletes it (recursively, via the object's cascade).
            NyTypeMeta.root().wrap(box_uuid).delete()
            return
        # user-type instance referenced from the array: not a box, keep it

    @classmethod
    @Database.commit_after_this
    def _ensure_array_instance(
        cls, owner_uuid: ObjectUUID, prop: NyProp, elem_type: str
    ) -> ArrayUUID:
        link = InstanceValues.link_for(owner_uuid, prop.uuid)
        if link is not None:
            return ArrayUUID.of(link.uuid)
        array_uuid = cls._create_array_instance(NyType.array_name(elem_type))
        InstanceValues.add_link(array_uuid, prop.uuid, owner_uuid)
        return array_uuid

    @classmethod
    @Database.commit_after_this
    def _create_array_instance(cls, array_type_name: str) -> ArrayUUID:
        array_uuid = uuid4()
        array_type = NyType.ensure(array_type_name)
        instances.create(array_uuid, array_type.uuid, Constants.Types.ARRAY_INSTANCE_NAME)
        return ArrayUUID.of(array_uuid)

    @classmethod
    @Database.use_same_session
    def _unwrap(cls, uuid: UUID, type_name: str) -> StoredValue:
        if NyType.is_array_name(type_name):
            return cls.read(ArrayUUID.of(uuid), NyType.element_name(type_name))
        if NyFile.is_file_type(type_name):
            # ADR-0008: a file element is a files.uuid, not a box instance
            return uuid
        scalar = NyScalar.by_type_name(type_name)
        if scalar is None and NyEnum.is_enum(type_name):
            # enum elements box as String boxes; membership was checked at write
            scalar = NyString
        if scalar is None:
            return NyTypeMeta.root().wrap(uuid)
        inst = instances.get(uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = NyType.by_uuid(TypeUUID.of(inst.type_uuid))
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        value_prop = NyProp.by_key(owner, Constants.Props.VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        stored = scalar.SCALAR.read(uuid, value_prop.uuid)
        return None if stored is None else scalar.from_storage(stored)

    @classmethod
    @Database.commit_after_this
    def _box(
        cls,
        type_name: str,
        value: StoredValue,
        array_uuid: ArrayUUID,
        owner_uuid: ObjectUUID,
        prop: NyProp,
        index: int,
    ) -> UUID:
        if NyType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(
                    f"{type_name} element takes list, got {type(value).__name__}"
                )
            nested_array_uuid = cls._create_array_instance(type_name)
            cls._fill(
                nested_array_uuid,
                NyType.element_name(type_name),
                value,
                owner_uuid,
                prop,
            )
            return nested_array_uuid
        scalar = NyScalar.by_type_name(type_name)
        if scalar is None:
            if NyFile.is_file_type(type_name):
                # ADR-0008: a file element stores its files.uuid directly in
                # value_uuid — no box instance (array_values.value_uuid is a
                # bare uuid after the ADR-0008 migration)
                if not isinstance(value, UUID):
                    raise TypeError(
                        f"{type_name} element takes a files.uuid, got {type(value).__name__}"
                    )
                if files.type_name_of(value) is None:
                    raise TypeError(f"{type_name} element references missing file {value}")
                return value
            if NyEnum.is_enum(type_name):
                validated = NyEnum.validate(type_name, value)
                scalar = NyString
                value = validated
            else:
                embedded = NyType.by_name(type_name)
                if embedded is not None and embedded.is_embedded:
                    # ADR-0021: an Array<Embedded> element is a composition
                    # child owned by the array instance, filled from its
                    # inline props draft and named <parent> → <prop> #<index>
                    return cls._box_embedded(
                        embedded, value, array_uuid, owner_uuid, prop, index
                    )
                NyTypeMeta.check_link(type_name, value)
                return cast(NyObjectShape, value).uuid
        NyScalar.validate(scalar.TYPE_NAME, cast(ScalarPayload | None, value))
        box_uuid = uuid4()
        owner = NyType.ensure(scalar.TYPE_NAME)
        instances.create(box_uuid, owner.uuid, str(value))
        value_prop = NyProp.by_key(owner, Constants.Props.VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        scalar.SCALAR.write(
            box_uuid,
            value_prop.uuid,
            scalar.to_storage(cast(ScalarPayload, value)),
        )
        return box_uuid

    @classmethod
    @Database.commit_after_this
    def _box_embedded(
        cls,
        embedded: NyType,
        draft: StoredValue,
        array_uuid: ArrayUUID,
        owner_uuid: ObjectUUID,
        prop: NyProp,
        index: int,
    ) -> ObjectUUID:
        if not isinstance(draft, dict):
            raise TypeError(
                f"{embedded.name} element takes a props dict, got {type(draft).__name__}"
            )
        return NyEmbedded.create_array_element(
            embedded,
            array_uuid,
            owner_uuid,
            prop,
            index,
            cast(dict[str, StoredValue], draft),
        )
