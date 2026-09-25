"""NyEmbedded: composition-typed props (ADR-0004).

An embedded-typed prop holds a child instance that exists only as that
prop's value: created lazily on first write, owned exclusively by the
(parent object, prop) pair, deleted with the parent or when the prop is
cleared. The child rides the ordinary instance_values link machinery;
the owner_* columns on instances are its read-side index.

Child names are generated: "<parent name> → <prop key>", recursively for
nesting. The → separator is reserved (validated at the Api boundary), so
generated names never collide with user-typed ones.

Never imports nyobject at all: child wrapping goes through
NyTypeMeta.root(), keeping the objects package acyclic (same trick as
NyArray).
"""
from __future__ import annotations

from typing import cast
from uuid import uuid4

from nylium.database import Database

from nylium.data.tables import instances
from nylium.data.tables import ArrayValues
from nylium.data.tables import InstanceValues
from nylium.data.tables import StringValues
from nylium.ny.NyProp import NyProp
from nylium.ny.NyType import NyType
from nylium.ny.NyTypeMeta import StoredValue, NyTypeMeta
from nylium.Constants import Constants
from nylium.uuid import ObjectUUID, PropUUID, TypeUUID


class NyEmbedded:
    @classmethod
    @Database.commit_after_this
    def write(
        cls,
        owner_uuid: ObjectUUID,
        prop: NyProp,
        draft: StoredValue,
    ) -> None:
        """Create-or-update the child from a props draft; None deletes it.
        The draft maps prop key -> value, exactly like an object write.
        Caller-supplied `name` values are ignored — names are generated."""
        link = InstanceValues.link_for(owner_uuid, prop.uuid)
        if draft is None:
            if link is not None:
                cls._destroy_child(ObjectUUID.of(link.uuid))
            return
        if not isinstance(draft, dict):
            raise TypeError(
                f"embedded prop takes a props dict, got {type(draft).__name__}"
            )
        if link is None:
            child_uuid = cls._create_child(owner_uuid, prop)
        else:
            child_uuid = ObjectUUID.of(link.uuid)
        cls._fill_child(child_uuid, cast(dict[str, StoredValue], draft))
        # name last: the parent's name prop may have been written in the
        # same request, and the generated name depends on it
        cls._write_generated_name(child_uuid, cls.generated_name(owner_uuid, prop))

    @classmethod
    def destroy(cls, child_uuid: ObjectUUID) -> None:
        """Delete the child instance; NyObject.delete cascades to its own
        embedded children and removes the parent's link row."""
        cls._destroy_child(child_uuid)

    @classmethod
    @Database.commit_after_this
    def destroy_children_of_prop(cls, prop_uuid: PropUUID) -> None:
        """Every child held through this prop, across all instances.
        Called from Api.sync_props before an embedded prop is deleted or
        retyped — otherwise the link rows cascade away and the child
        instances orphan. For an Array<Embedded> prop the link rows point
        at the array instances; deleting one cascades (via its own
        lifecycle) to the composed elements."""
        child_uuids = InstanceValues.linked_uuids_of(prop_uuid)
        for child_uuid in child_uuids:
            cls._destroy_child(ObjectUUID.of(child_uuid))

    @classmethod
    @Database.commit_after_this
    def regenerate_names(cls, object_uuid: ObjectUUID) -> None:
        """Rewrite generated names of this object's embedded children
        (composition links and Array<Embedded> elements), then recurse —
        grandchild names embed the child name. The instance graph is a
        tree (children are always created fresh), so the recursion
        terminates."""
        inst = instances.get(object_uuid)
        if inst is None:
            return
        owner = NyType.by_uuid(TypeUUID.of(inst.type_uuid))
        if owner is None:
            return
        for prop in NyProp.effective_for(owner):
            if prop.is_trait_bound:
                continue
            value_type = prop.value_type()
            if value_type.is_embedded:
                link = InstanceValues.link_for(object_uuid, prop.uuid)
                if link is None:
                    continue
                cls._write_generated_name(ObjectUUID.of(link.uuid), cls.generated_name(object_uuid, prop))
                cls.regenerate_names(ObjectUUID.of(link.uuid))
                continue
            # ADR-0021: Array<Embedded> elements are named
            # "<parent> → <prop key> #<index>" and owned by the array
            # instance, not the parent — regenerate each in index order.
            if cls.array_element_type(value_type) is None:
                continue
            array_link = InstanceValues.link_for(object_uuid, prop.uuid)
            if array_link is None:
                continue
            for index, element_uuid in enumerate(ArrayValues.element_uuids_of(array_link.uuid)):
                cls._write_generated_name(
                    ObjectUUID.of(element_uuid), cls.array_element_name(object_uuid, prop, index)
                )
                cls.regenerate_names(ObjectUUID.of(element_uuid))

    @classmethod
    @Database.use_same_session
    def generated_name(cls, owner_uuid: ObjectUUID, prop: NyProp) -> str:
        """"<parent display name> → <prop key>". Falls back to the
        registry name (Type:shortuuid) while the parent's name prop is
        still unset — a later name write regenerates it."""
        base: str | None = None
        inst = instances.get(owner_uuid)
        if inst is not None:
            owner = NyType.by_uuid(TypeUUID.of(inst.type_uuid))
            if owner is not None:
                name_prop = NyProp.by_key(owner, Constants.Props.NAME_PROP_KEY)
                if name_prop is not None:
                    base = cast(
                        str | None, StringValues.read(owner_uuid, name_prop.uuid)
                    )
            if not base:
                base = inst.name
        if not base:
            base = str(owner_uuid)
        return f"{base} {Constants.Embedded.NAME_SEPARATOR} {prop.key}"

    @classmethod
    @Database.use_same_session
    def array_element_type(cls, value_type: NyType) -> NyType | None:
        """ADR-0021: the embedded element type when ``value_type`` names an
        Array<Embedded>, else None."""
        if not NyType.is_array_name(value_type.name):
            return None
        element = NyType.by_name(NyType.element_name(value_type.name))
        if element is not None and element.is_embedded:
            return element
        return None

    @classmethod
    def array_element_name(cls, owner_uuid: ObjectUUID, prop: NyProp, index: int) -> str:
        """ADR-0021: '<parent> → <prop key> #<index>' (1-based)."""
        return f"{cls.generated_name(owner_uuid, prop)} #{index + 1}"

    @classmethod
    @Database.commit_after_this
    def create_array_element(
        cls,
        embedded: NyType,
        array_uuid: ObjectUUID,
        owner_uuid: ObjectUUID,
        prop: NyProp,
        index: int,
        draft: dict[str, StoredValue],
    ) -> ObjectUUID:
        """ADR-0021: create one embedded child of an Array<Embedded> prop.

        The child is owned by the array instance (owner_object_uuid =
        array_uuid), filled from its inline props draft, and named
        ``<parent> → <prop key> #<index>`` (1-based)."""
        child_uuid = ObjectUUID.of(uuid4())
        instances.create(
            child_uuid,
            embedded.uuid,
            Constants.Objects.INSTANCE_NAME_FORMAT.format(
                type_name=embedded.name,
                short_uuid=str(child_uuid)[:Constants.Objects.SHORT_UUID_LENGTH],
            ),
            owner_object_uuid=array_uuid,
            owner_prop_uuid=None,
        )
        cls._fill_child(child_uuid, draft)
        cls._write_generated_name(child_uuid, cls.array_element_name(owner_uuid, prop, index))
        return child_uuid

    # --- internals ---

    @classmethod
    @Database.commit_after_this
    def _create_child(cls, owner_uuid: ObjectUUID, prop: NyProp) -> ObjectUUID:
        child_type = prop.value_type()
        child_uuid = ObjectUUID.of(uuid4())
        instances.create(
            child_uuid,
            child_type.uuid,
            Constants.Objects.INSTANCE_NAME_FORMAT.format(
                type_name=child_type.name,
                short_uuid=str(child_uuid)[:Constants.Objects.SHORT_UUID_LENGTH],
            ),
            owner_object_uuid=owner_uuid,
            owner_prop_uuid=prop.uuid,
        )
        InstanceValues.add_link(child_uuid, prop.uuid, owner_uuid)
        return child_uuid

    @classmethod
    def _fill_child(cls, child_uuid: ObjectUUID, props: dict[str, StoredValue]) -> None:
        child = NyTypeMeta.root().wrap(child_uuid)
        for key, value in props.items():
            if key == Constants.Props.NAME_PROP_KEY:
                continue  # caller-supplied names are ignored — generated only
            setattr(child, key, value)

    @classmethod
    def _write_generated_name(cls, child_uuid: ObjectUUID, name: str) -> None:
        child = NyTypeMeta.root().wrap(child_uuid)
        inst = instances.get(child_uuid)
        owner = NyType.by_uuid(TypeUUID.of(inst.type_uuid)) if inst is not None else None
        if owner is None or NyProp.by_key(owner, Constants.Props.NAME_PROP_KEY) is None:
            return  # name-less embedded type (ADR-0027) keeps its registry name
        setattr(child, Constants.Props.NAME_PROP_KEY, name)

    @classmethod
    def _destroy_child(cls, child_uuid: ObjectUUID) -> None:
        NyTypeMeta.root().wrap(child_uuid).delete()
