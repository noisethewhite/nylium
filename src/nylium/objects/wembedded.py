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

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database, Instances, InstanceValues, StringValues
from nylium.objects.wprop import WProp
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
    @Database.sessionmethod(bundled=False, commit=True)
    def write(
        cls,
        session: Session,
        owner_uuid: UUID,
        prop: WProp,
        draft: StoredValue,
    ) -> None:
        """Create-or-update the child from a props draft; None deletes it.
        The draft maps prop key -> value, exactly like an object write.
        Caller-supplied `name` values are ignored — names are generated."""
        link = session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == owner_uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )
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
    @Database.sessionmethod(bundled=False, commit=True)
    def destroy_children_of_prop(cls, session: Session, prop_uuid: UUID) -> None:
        """Every child linked through this prop, across all instances.
        Called from Api.sync_props before an embedded prop is deleted or
        retyped — otherwise the link rows cascade away and the child
        instances orphan."""
        child_uuids = list(
            session.scalars(
                sqla.select(InstanceValues.uuid).where(
                    InstanceValues.prop_uuid == prop_uuid
                )
            ).all()
        )
        for child_uuid in child_uuids:
            cls._destroy_child(child_uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def regenerate_names(cls, session: Session, object_uuid: UUID) -> None:
        """Rewrite generated names of this object's embedded children,
        then recurse — grandchild names embed the child name. The
        instance graph is a tree (children are always created fresh),
        so the recursion terminates."""
        inst = session.get(Instances, object_uuid)
        if inst is None:
            return
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            return
        for prop in WProp.all_for(owner):
            if not prop.value_type().is_embedded:
                continue
            link = session.scalar(
                sqla.select(InstanceValues).where(
                    InstanceValues.inst_uuid == object_uuid,
                    InstanceValues.prop_uuid == prop.uuid,
                )
            )
            if link is None:
                continue
            cls._write_generated_name(link.uuid, cls.generated_name(object_uuid, prop))
            cls.regenerate_names(link.uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def generated_name(cls, session: Session, owner_uuid: UUID, prop: WProp) -> str:
        """"<parent display name> → <prop key>". Falls back to the
        registry name (Type:shortuuid) while the parent's name prop is
        still unset — a later name write regenerates it."""
        base: str | None = None
        inst = session.get(Instances, owner_uuid)
        if inst is not None:
            owner = WType.by_uuid(inst.type_uuid)
            if owner is not None:
                name_prop = WProp.by_key(owner, NAME_PROP_KEY)
                if name_prop is not None:
                    row = session.get(StringValues, (owner_uuid, name_prop.uuid))
                    base = None if row is None else cast(str | None, row.value)
            if not base:
                base = inst.name
        if not base:
            base = str(owner_uuid)
        return f"{base} {EMBEDDED_NAME_SEPARATOR} {prop.key}"

    # --- internals ---

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def _create_child(cls, session: Session, owner_uuid: UUID, prop: WProp) -> UUID:
        child_type = prop.value_type()
        child_uuid = uuid4()
        Instances.register(
            child_uuid,
            child_type.uuid,
            REGISTRY_NAME_FORMAT.format(
                type_name=child_type.name,
                short_uuid=str(child_uuid)[:SHORT_UUID_LENGTH],
            ),
            owner_object_uuid=owner_uuid,
            owner_prop_uuid=prop.uuid,
        )
        # flush before the link row: without ORM relationships the
        # pending-insert order is arbitrary, and instance_values.uuid
        # FKs into instances
        session.flush()
        session.add(
            InstanceValues(uuid=child_uuid, prop_uuid=prop.uuid, inst_uuid=owner_uuid)
        )
        session.flush()
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
        setattr(WTypeMeta.root().wrap(child_uuid), NAME_PROP_KEY, name)

    @classmethod
    def _destroy_child(cls, child_uuid: UUID) -> None:
        WTypeMeta.root().wrap(child_uuid).delete()
