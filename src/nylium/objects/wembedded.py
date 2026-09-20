"""WEmbedded: composition-typed props (ADR-0004).

An embedded-typed prop holds a child instance that exists only as that
prop's value: created lazily on first write, owned exclusively by the
(parent object, prop) pair, deleted with the parent or when the prop is
cleared. The child rides the ordinary instance_values link machinery;
the owner_* columns on instances are its read-side index.

Child names are generated: "<parent name> → <prop key>", recursively for
nesting. The → separator is reserved (validated at the Api boundary), so
generated names never collide with user-typed ones.

Never imports wobject at all: child wrapping goes through
WTypeMeta.root(), keeping the objects package acyclic (same trick as
WArray).
"""
from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from nylium.database import Database

from nylium.tables.objects import instances
from nylium.tables.values.array_values_store import ArrayValues
from nylium.tables.values.instance_values_store import InstanceValues
from nylium.objects.wprop import WProp
from nylium.tables.values.string_values_store import StringValues
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta

EMBEDDED_NAME_SEPARATOR = "→"
# mirrors api.NAME_PROP_KEY; api imports the object layer, so the
# constant can't be imported from there without a cycle
NAME_PROP_KEY = "name"
REGISTRY_NAME_FORMAT = "{type_name}:{short_uuid}"
SHORT_UUID_LENGTH = 8


class WEmbedded:
    @classmethod
    @Database.commit_after_this
    def write(
        cls,
        owner_uuid: UUID,
        prop: WProp,
        draft: StoredValue,
    ) -> None:
        """Create-or-update the child from a props draft; None deletes it.
        The draft maps prop key -> value, exactly like an object write.
        Caller-supplied `name` values are ignored — names are generated."""
        link = InstanceValues.link_for(owner_uuid, prop.uuid)
        if draft is None:
            if link is not None:
                cls._destroy_child(link.uuid)
            return
        if not isinstance(draft, dict):
            raise TypeError(
                f"embedded prop takes a props dict, got {type(draft).__name__}"
            )
        if link is None:
            child_uuid = cls._create_child(owner_uuid, prop)
        else:
            child_uuid = link.uuid
        cls._fill_child(child_uuid, cast(dict[str, StoredValue], draft))
        # name last: the parent's name prop may have been written in the
        # same request, and the generated name depends on it
        cls._write_generated_name(child_uuid, cls.generated_name(owner_uuid, prop))

    @classmethod
    def destroy(cls, child_uuid: UUID) -> None:
        """Delete the child instance; WObject.delete cascades to its own
        embedded children and removes the parent's link row."""
        cls._destroy_child(child_uuid)

    @classmethod
    @Database.commit_after_this
    def destroy_children_of_prop(cls, prop_uuid: UUID) -> None:
        """Every child held through this prop, across all instances.
        Called from Api.sync_props before an embedded prop is deleted or
        retyped — otherwise the link rows cascade away and the child
        instances orphan. For an Array<Embedded> prop the link rows point
        at the array instances; deleting one cascades (via its own
        lifecycle) to the composed elements."""
        child_uuids = InstanceValues.linked_uuids_of(prop_uuid)
        for child_uuid in child_uuids:
            cls._destroy_child(child_uuid)

    @classmethod
    @Database.commit_after_this
    def regenerate_names(cls, object_uuid: UUID) -> None:
        """Rewrite generated names of this object's embedded children
        (composition links and Array<Embedded> elements), then recurse —
        grandchild names embed the child name. The instance graph is a
        tree (children are always created fresh), so the recursion
        terminates."""
        inst = instances.get(object_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            return
        for prop in WProp.effective_for(owner):
            if prop.is_trait_bound:
                continue
            value_type = prop.value_type()
            if value_type.is_embedded:
                link = InstanceValues.link_for(object_uuid, prop.uuid)
                if link is None:
                    continue
                cls._write_generated_name(link.uuid, cls.generated_name(object_uuid, prop))
                cls.regenerate_names(link.uuid)
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
                    element_uuid, cls.array_element_name(object_uuid, prop, index)
                )
                cls.regenerate_names(element_uuid)

    @classmethod
    @Database.use_same_session
    def generated_name(cls, owner_uuid: UUID, prop: WProp) -> str:
        """"<parent display name> → <prop key>". Falls back to the
        registry name (Type:shortuuid) while the parent's name prop is
        still unset — a later name write regenerates it."""
        base: str | None = None
        inst = instances.get(owner_uuid)
        if inst is not None:
            owner = WType.by_uuid(inst.type_uuid)
            if owner is not None:
                name_prop = WProp.by_key(owner, NAME_PROP_KEY)
                if name_prop is not None:
                    base = cast(
                        str | None, StringValues.read(owner_uuid, name_prop.uuid)
                    )
            if not base:
                base = inst.name
        if not base:
            base = str(owner_uuid)
        return f"{base} {EMBEDDED_NAME_SEPARATOR} {prop.key}"

    @classmethod
    @Database.use_same_session
    def array_element_type(cls, value_type: WType) -> WType | None:
        """ADR-0021: the embedded element type when ``value_type`` names an
        Array<Embedded>, else None."""
        if not WType.is_array_name(value_type.name):
            return None
        element = WType.by_name(WType.element_name(value_type.name))
        if element is not None and element.is_embedded:
            return element
        return None

    @classmethod
    def array_element_name(cls, owner_uuid: UUID, prop: WProp, index: int) -> str:
        """ADR-0021: '<parent> → <prop key> #<index>' (1-based)."""
        return f"{cls.generated_name(owner_uuid, prop)} #{index + 1}"

    @classmethod
    @Database.commit_after_this
    def create_array_element(
        cls,
        embedded: WType,
        array_uuid: UUID,
        owner_uuid: UUID,
        prop: WProp,
        index: int,
        draft: dict[str, StoredValue],
    ) -> UUID:
        """ADR-0021: create one embedded child of an Array<Embedded> prop.

        The child is owned by the array instance (owner_object_uuid =
        array_uuid), filled from its inline props draft, and named
        ``<parent> → <prop key> #<index>`` (1-based)."""
        child_uuid = uuid4()
        instances.create(
            child_uuid,
            embedded.uuid,
            REGISTRY_NAME_FORMAT.format(
                type_name=embedded.name,
                short_uuid=str(child_uuid)[:SHORT_UUID_LENGTH],
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
    def _create_child(cls, owner_uuid: UUID, prop: WProp) -> UUID:
        child_type = prop.value_type()
        child_uuid = uuid4()
        instances.create(
            child_uuid,
            child_type.uuid,
            REGISTRY_NAME_FORMAT.format(
                type_name=child_type.name,
                short_uuid=str(child_uuid)[:SHORT_UUID_LENGTH],
            ),
            owner_object_uuid=owner_uuid,
            owner_prop_uuid=prop.uuid,
        )
        InstanceValues.add_link(child_uuid, prop.uuid, owner_uuid)
        return child_uuid

    @classmethod
    def _fill_child(cls, child_uuid: UUID, props: dict[str, StoredValue]) -> None:
        child = WTypeMeta.root().wrap(child_uuid)
        for key, value in props.items():
            if key == NAME_PROP_KEY:
                continue  # caller-supplied names are ignored — generated only
            setattr(child, key, value)

    @classmethod
    def _write_generated_name(cls, child_uuid: UUID, name: str) -> None:
        child = WTypeMeta.root().wrap(child_uuid)
        inst = instances.get(child_uuid)
        owner = WType.by_uuid(inst.type_uuid) if inst is not None else None
        if owner is None or WProp.by_key(owner, NAME_PROP_KEY) is None:
            return  # name-less embedded type (ADR-0027) keeps its registry name
        setattr(child, NAME_PROP_KEY, name)

    @classmethod
    def _destroy_child(cls, child_uuid: UUID) -> None:
        WTypeMeta.root().wrap(child_uuid).delete()
