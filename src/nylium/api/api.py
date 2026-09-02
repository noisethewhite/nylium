"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning the dataclass views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a view, a UUID, or a plain python value. Writes go through the
WObject layer, so all type validation applies here too.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.api.views import (
    ArrayValue,
    ObjectRef,
    ObjectView,
    PropValue,
    PropView,
    RefValue,
    ScalarValue,
    TypeView,
)
from nylium.database import Database, Instances, Types
from nylium.objects.wobject import INSTANCE_NAME_FORMAT, SHORT_UUID_LENGTH, WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta

# What callers may hand in for a prop: stored values, plus links as
# UUID/ObjectRef (resolved to WObject here). A string forward ref inside
# list[...] keeps the recursion 3.11-parseable without typing.Union.
PropInput: TypeAlias = StoredValue | UUID | ObjectRef | list["PropInput"]


class Api:
    # --- types ---

    @classmethod
    @Database.sessionmethod.no_commit
    def list_types(cls, session: Session) -> list[TypeView]:
        names = list(session.scalars(sqla.select(Types.name)).all())
        return [cls._type_view(name) for name in names]

    @classmethod
    @Database.sessionmethod.bundled_no_commit
    def get_type(cls, name: str) -> TypeView | None:
        if WType.by_name(name) is None:
            return None
        return cls._type_view(name)

    @classmethod
    @Database.sessionmethod.bundled_with_commit
    def create_type(cls, name: str, props: dict[str, str] | None = None) -> TypeView:
        """props maps key -> value type name. Missing value types are created."""
        WScalar.ensure_builtins()
        owner = WType.ensure(name)
        for key, value_type_name in (props or {}).items():
            _ = WProp.ensure(owner, key, WType.ensure(value_type_name))
        return cls._type_view(name)

    @classmethod
    @Database.sessionmethod.with_commit
    def delete_type(cls, session: Session, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""
        owner = WType.by_name(name)
        if owner is None:
            return False
        instance_count = session.scalar(
            sqla.select(sqla.func.count())
            .select_from(Instances)
            .where(Instances.type_uuid == owner.uuid)
        )
        if instance_count:
            raise ValueError(
                f"type {name!r} still has {instance_count} instances"
            )
        row = session.get(Types, owner.uuid)
        if row is not None:
            session.delete(row)  # its props cascade
        return True

    # --- objects ---

    @classmethod
    @Database.sessionmethod.no_commit
    def list_objects(cls, session: Session, type_name: str) -> list[ObjectView]:
        owner = WType.by_name(type_name)
        if owner is None:
            return []
        uuids = list(
            session.scalars(
                sqla.select(Instances.uuid).where(
                    Instances.type_uuid == owner.uuid
                )
            ).all()
        )
        views = [cls._object_view(uuid) for uuid in uuids]
        return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        return cls._object_view(uuid)

    @classmethod
    @Database.sessionmethod.bundled_with_commit
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
            instance_uuid = cls._create_db_only(type_name, normalized)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod.bundled_with_commit
    def update_object(cls, uuid: UUID, props: dict[str, PropInput]) -> ObjectView:
        wrapper = WObject.wrap(uuid)
        type_name = cls._type_name_of(uuid)
        normalized = cls._normalize_props(type_name, props)
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod.with_commit
    def delete_object(cls, session: Session, uuid: UUID) -> bool:
        if session.get(Instances, uuid) is None:
            return False
        WObject.wrap(uuid).delete()
        return True

    # --- internals ---

    @classmethod
    @Database.sessionmethod.bundled_no_commit
    def _normalize_props(
        cls, type_name: str, props: dict[str, PropInput]
    ) -> dict[str, StoredValue]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        return {
            key: cls._normalize_value(value, cls._prop_type_name(owner, key))
            for key, value in props.items()
        }

    @classmethod
    @Database.sessionmethod.bundled_no_commit
    def _prop_type_name(cls, owner: WType, key: str) -> str:
        prop = WProp.by_key(owner, key)
        if prop is None:
            raise KeyError(f"type {owner.name!r} has no prop {key!r}")
        return prop.value_type().name

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

    @classmethod
    @Database.sessionmethod.bundled_no_commit
    def _type_view(cls, name: str) -> TypeView:
        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        return TypeView(
            name=name,
            props=[
                PropView(key=prop.key, value_type=prop.value_type().name)
                for prop in WProp.all_for(owner)
            ],
        )

    @classmethod
    @Database.sessionmethod.with_commit
    def _create_db_only(cls, session: Session, type_name: str, props: dict[str, StoredValue]) -> UUID:
        """Types with no registered python class: bare instance row, then
        writes through the generic WObject wrapper — same validation."""
        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        instance_uuid = uuid4()
        session.add(
            Instances(
                uuid=instance_uuid,
                type_uuid=owner.uuid,
                name=INSTANCE_NAME_FORMAT.format(
                    type_name=type_name,
                    short_uuid=str(instance_uuid)[:SHORT_UUID_LENGTH],
                ),
            )
        )
        wrapper = WObject.wrap(instance_uuid)
        for key, value in props.items():
            setattr(wrapper, key, value)
        return instance_uuid

    @classmethod
    @Database.sessionmethod.no_commit
    def _object_view(cls, session: Session, uuid: UUID) -> ObjectView | None:
        inst = session.get(Instances, uuid)
        if inst is None:
            return None
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        wrapper = WObject.wrap(uuid)
        props = {
            prop.key: cls._render(
                cast(StoredValue, getattr(wrapper, prop.key)),
                prop.value_type().name,
            )
            for prop in WProp.all_for(owner)
        }
        return ObjectView(uuid=uuid, type_name=owner.name, props=props)

    @classmethod
    def _render(cls, value: StoredValue, type_name: str) -> PropValue:
        """The declared prop type disambiguates None: an unset scalar,
        an unset link and an unset array are three different views."""
        if WScalar.by_type_name(type_name) is not None:
            return ScalarValue(value=cast(ScalarPayload | None, value))
        if WType.is_array_name(type_name):
            element_name = WType.element_name(type_name)
            if value is None:
                return ArrayValue(items=None)
            if not isinstance(value, list):
                raise TypeError(f"array prop rendered a {type(value).__name__}")
            return ArrayValue(
                items=[cls._render(item, element_name) for item in value]
            )
        if value is None:
            return RefValue(ref=None)
        if not isinstance(value, WObject):
            raise TypeError(f"link prop rendered a {type(value).__name__}")
        return RefValue(
            ref=ObjectRef(uuid=value.uuid, type_name=cls._type_name_of(value.uuid))
        )

    @classmethod
    @Database.sessionmethod.no_commit
    def _type_name_of(cls, session: Session, uuid: UUID) -> str:
        inst = session.get(Instances, uuid)
        if inst is None:
            return "<gone>"
        owner = WType.by_uuid(inst.type_uuid)
        return "<dangling>" if owner is None else owner.name
