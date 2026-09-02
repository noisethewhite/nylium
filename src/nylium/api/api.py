"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning the dataclass views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a view, a UUID, or a plain python value. Writes go through the
WObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/Instances/
Props helpers); this file only orchestrates and adapts caller input.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias, cast
from uuid import UUID

from nylium.api.views import ObjectRef, ObjectView, TypeView
from nylium.database import Database, Instances, Props, Types
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta

# What callers may hand in for a prop: stored values, plus links as
# UUID/ObjectRef (resolved to WObject here). A string forward ref inside
# list[...] keeps the recursion 3.11-parseable without typing.Union.
PropInput: TypeAlias = StoredValue | UUID | ObjectRef | list["PropInput"]


class Api:
    # --- types ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def list_types(cls) -> list[TypeView]:
        return [TypeView.from_name(name) for name in Types.all_names()]

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def get_type(cls, name: str) -> TypeView | None:
        if WType.by_name(name) is None:
            return None
        return TypeView.from_name(name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_type(
        cls,
        name: str,
        props: dict[str, str] | None = None,
        plural_name: str | None = None,
    ) -> TypeView:
        """props maps key -> value type name. Missing value types are created."""
        WScalar.ensure_builtins()
        owner = WType.ensure(name, plural_name)
        for key, value_type_name in (props or {}).items():
            _ = WProp.ensure(owner, key, WType.ensure(value_type_name))
        return TypeView.from_name(name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def delete_type(cls, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""
        owner = WType.by_name(name)
        if owner is None:
            return False
        instance_count = Instances.count_of_type(owner.uuid)
        if instance_count:
            raise ValueError(
                f"type {name!r} still has {instance_count} instances"
            )
        Types.delete_by_uuid(owner.uuid)
        return True

    # --- objects ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        owner = WType.by_name(type_name)
        if owner is None:
            return []
        views = [
            ObjectView.from_uuid(uuid)
            for uuid in Instances.uuids_of_type(owner.uuid)
        ]
        return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        return ObjectView.from_uuid(uuid)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_object(
        cls, type_name: str, props: dict[str, PropInput] | None = None
    ) -> ObjectView:
        normalized = cls._normalize_props(type_name, props or {})
        klass = WTypeMeta.python_class(type_name)
        if klass is not None:
            # **props forwarding: the dict can't collide with _uuid in
            # practice (prop keys), but the checker can't prove it
            ctor = cast(Callable[..., WObject], klass)
            instance_uuid = ctor(**normalized).uuid
        else:
            instance_uuid = WObject.create_db_only(type_name, normalized)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def update_object(cls, uuid: UUID, props: dict[str, PropInput]) -> ObjectView:
        wrapper = WObject.wrap(uuid)
        type_name = Instances.get_type_name(uuid)
        normalized = cls._normalize_props(type_name, props)
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def delete_object(cls, uuid: UUID) -> bool:
        if not Instances.exists(uuid):
            return False
        WObject.wrap(uuid).delete()
        return True

    # --- internals ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def _normalize_props(
        cls, type_name: str, props: dict[str, PropInput]
    ) -> dict[str, StoredValue]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        owner_type_uuid = Types.uuid_by_name(type_name)
        if owner_type_uuid is None:
            raise KeyError(f"no type {type_name!r}")
        return {
            key: cls._normalize_value(value, Props.get_type_name(owner_type_uuid, key))
            for key, value in props.items()
        }

    @classmethod
    def _normalize_value(cls, value: PropInput, type_name: str) -> StoredValue:
        if WScalar.by_type_name(type_name) is not None:
            return cast(StoredValue, value)
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(f"array prop takes list, got {type(value).__name__}")
            element_name = WType.element_name(type_name)
            return [cls._normalize_value(item, element_name) for item in value]
        if isinstance(value, ObjectRef):
            return WObject.wrap(value.uuid)
        if isinstance(value, UUID):
            return WObject.wrap(value)
        return cast(StoredValue, value)  # anything else fails in setattr
