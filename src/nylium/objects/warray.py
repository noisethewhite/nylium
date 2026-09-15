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

from nylium.database import databasemethod
from nylium.tables import instances
from nylium.tables.files import type_name_of as file_type_name_of
from nylium.tables.objects.instances import delete_row as delete_instance_row, get as instance_get
from nylium.tables.values import cells
from nylium.tables.values.array_values import (
    add_element,
    delete_elements_of,
    element_uuids_of,
)
from nylium.tables.values.instance_values import add_link, delete_links_to, link_for
from nylium.objects.wenum import WEnum
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wfile import WFile
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import VALUE_PROP_KEY, ScalarPayload, WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WObjectShape, WTypeMeta

ARRAY_INSTANCE_NAME = "array"


class WArray:
    @classmethod
    @databasemethod(commit=False)
    def read(cls, array_uuid: UUID, elem_type: str) -> list[StoredValue]:
        return [cls._unwrap(uuid, elem_type) for uuid in element_uuids_of(array_uuid)]

    @classmethod
    @databasemethod(commit=True)
    def write(
        cls,
        owner_uuid: UUID,
        prop: WProp,
        elem_type: str,
        values: list[StoredValue] | None,
    ) -> None:
        if values is None:
            # None unsets the prop: destroy the array instance (and its boxes)
            link = link_for(owner_uuid, prop.uuid)
            if link is not None:
                cls.destroy(link.uuid)
            return
        array_uuid = cls._ensure_array_instance(owner_uuid, prop, elem_type)
        cls._fill(array_uuid, elem_type, values, owner_uuid, prop)

    @classmethod
    @databasemethod(commit=True)
    def destroy(cls, array_uuid: UUID) -> None:
        """Delete the array instance and every box it owns, recursively."""
        cls._destroy_boxes(array_uuid)
        delete_links_to(array_uuid)
        delete_instance_row(array_uuid)

    # --- internals ---

    @classmethod
    @databasemethod(commit=True)
    def _fill(
        cls,
        array_uuid: UUID,
        elem_type: str,
        values: list[StoredValue],
        owner_uuid: UUID,
        prop: WProp,
    ) -> None:
        cls._destroy_boxes(array_uuid)
        for index, item in enumerate(values):
            add_element(
                array_uuid, index, cls._box(elem_type, item, array_uuid, owner_uuid, prop, index)
            )

    @classmethod
    @databasemethod(commit=True)
    def _destroy_boxes(cls, array_uuid: UUID) -> None:
        box_uuids = element_uuids_of(array_uuid)
        # detach pointer rows first: FK array_values.value_uuid -> instances
        # forbids deleting a box that is still referenced
        delete_elements_of(array_uuid)
        for box_uuid in box_uuids:
            cls._destroy_box(box_uuid)

    @classmethod
    @databasemethod(commit=True)
    def _destroy_box(cls, box_uuid: UUID) -> None:
        inst = instance_get(box_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {box_uuid} has dangling type")
        if WScalar.is_scalar(owner.name):
            delete_instance_row(box_uuid)  # its scalar values cascade on inst_uuid
            return
        if WType.is_array_name(owner.name):
            cls.destroy(box_uuid)
            return
        if owner.is_embedded:
            # ADR-0021: an Array<Embedded> element is a composition child —
            # its lifecycle is owned by the array, so a rewrite/delete of
            # the array deletes it (recursively, via the object's cascade).
            WTypeMeta.root().wrap(box_uuid).delete()
            return
        # user-type instance referenced from the array: not a box, keep it

    @classmethod
    @databasemethod(commit=True)
    def _ensure_array_instance(
        cls, owner_uuid: UUID, prop: WProp, elem_type: str
    ) -> UUID:
        link = link_for(owner_uuid, prop.uuid)
        if link is not None:
            return link.uuid
        array_uuid = cls._create_array_instance(WType.array_name(elem_type))
        add_link(array_uuid, prop.uuid, owner_uuid)
        return array_uuid

    @classmethod
    @databasemethod(commit=True)
    def _create_array_instance(cls, array_type_name: str) -> UUID:
        array_uuid = uuid4()
        array_type = WType.ensure(array_type_name)
        instances.create(array_uuid, array_type.uuid, ARRAY_INSTANCE_NAME)
        return array_uuid

    @classmethod
    @databasemethod(commit=False)
    def _unwrap(cls, uuid: UUID, type_name: str) -> StoredValue:
        if WType.is_array_name(type_name):
            return cls.read(uuid, WType.element_name(type_name))
        if WFile.is_file_type(type_name):
            # ADR-0008: a file element is a files.uuid, not a box instance
            return uuid
        scalar = WScalar.by_type_name(type_name)
        if scalar is None and WEnum.is_enum(type_name):
            # enum elements box as String boxes; membership was checked at write
            scalar = WString
        if scalar is None:
            return WTypeMeta.root().wrap(uuid)
        inst = instance_get(uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        value_prop = WProp.by_key(owner, VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        stored = cells.read(scalar.TABLE, uuid, value_prop.uuid)
        return None if stored is None else scalar.from_storage(stored)

    @classmethod
    @databasemethod(commit=True)
    def _box(
        cls,
        type_name: str,
        value: StoredValue,
        array_uuid: UUID,
        owner_uuid: UUID,
        prop: WProp,
        index: int,
    ) -> UUID:
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(
                    f"{type_name} element takes list, got {type(value).__name__}"
                )
            nested_array_uuid = cls._create_array_instance(type_name)
            cls._fill(
                nested_array_uuid,
                WType.element_name(type_name),
                value,
                owner_uuid,
                prop,
            )
            return nested_array_uuid
        scalar = WScalar.by_type_name(type_name)
        if scalar is None:
            if WFile.is_file_type(type_name):
                # ADR-0008: a file element stores its files.uuid directly in
                # value_uuid — no box instance (array_values.value_uuid is a
                # bare uuid after the ADR-0008 migration)
                if not isinstance(value, UUID):
                    raise TypeError(
                        f"{type_name} element takes a files.uuid, got {type(value).__name__}"
                    )
                if file_type_name_of(value) is None:
                    raise TypeError(f"{type_name} element references missing file {value}")
                return value
            if WEnum.is_enum(type_name):
                validated = WEnum.validate(type_name, value)
                scalar = WString
                value = validated
            else:
                embedded = WType.by_name(type_name)
                if embedded is not None and embedded.is_embedded:
                    # ADR-0021: an Array<Embedded> element is a composition
                    # child owned by the array instance, filled from its
                    # inline props draft and named <parent> → <prop> #<index>
                    return cls._box_embedded(
                        embedded, value, array_uuid, owner_uuid, prop, index
                    )
                WTypeMeta.check_link(type_name, value)
                return cast(WObjectShape, value).uuid
        WScalar.validate(scalar.TYPE_NAME, cast(ScalarPayload | None, value))
        box_uuid = uuid4()
        owner = WType.ensure(scalar.TYPE_NAME)
        instances.create(box_uuid, owner.uuid, str(value))
        value_prop = WProp.by_key(owner, VALUE_PROP_KEY)
        if value_prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its 'value' prop")
        cells.write(
            scalar.TABLE,
            box_uuid,
            value_prop.uuid,
            scalar.to_storage(cast(ScalarPayload, value)),
        )
        return box_uuid

    @classmethod
    @databasemethod(commit=True)
    def _box_embedded(
        cls,
        embedded: WType,
        draft: StoredValue,
        array_uuid: UUID,
        owner_uuid: UUID,
        prop: WProp,
        index: int,
    ) -> UUID:
        if not isinstance(draft, dict):
            raise TypeError(
                f"{embedded.name} element takes a props dict, got {type(draft).__name__}"
            )
        return WEmbedded.create_array_element(
            embedded,
            array_uuid,
            owner_uuid,
            prop,
            index,
            cast(dict[str, StoredValue], draft),
        )
