"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning the dataclass views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a view, a UUID, or a plain python value. Writes go through the
WObject layer, so all type validation applies here too.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.api.views import ObjectRef, ObjectView, PropView, TypeView
from whiteout.database.tables import Instances, Types
from whiteout.objects.sessions import sessions
from whiteout.objects.wobject import INSTANCE_NAME_FORMAT, SHORT_UUID_LENGTH, WObject
from whiteout.objects.wscalar import WScalar
from whiteout.objects.wtype import WType
from whiteout.objects.wtypemeta import WTypeMeta


class Api:
    # --- types ---

    @classmethod
    def list_types(cls) -> list[TypeView]:
        with sessions.new() as session:
            names = list(session.scalars(sqla.select(Types.name)).all())
            return [cls._type_view(session, name) for name in names]

    @classmethod
    def get_type(cls, name: str) -> TypeView | None:
        with sessions.new() as session:
            if WType.by_name(session, name) is None:
                return None
            return cls._type_view(session, name)

    @classmethod
    def create_type(cls, name: str, props: dict[str, str] | None = None) -> TypeView:
        """props maps key -> value type name. Missing value types are created."""
        with sessions.new() as session, session.begin():
            owner = WType.ensure(session, name)
            for key, value_type_name in (props or {}).items():
                _ = owner.ensure_prop(session, key, WType.ensure(session, value_type_name))
            return cls._type_view(session, name)

    @classmethod
    def delete_type(cls, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""
        with sessions.new() as session, session.begin():
            owner = WType.by_name(session, name)
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
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        with sessions.new() as session:
            owner = WType.by_name(session, type_name)
            if owner is None:
                return []
            uuids = list(
                session.scalars(
                    sqla.select(Instances.uuid).where(
                        Instances.type_uuid == owner.uuid
                    )
                ).all()
            )
            views = [cls._object_view(session, uuid) for uuid in uuids]
            return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        with sessions.new() as session:
            return cls._object_view(session, uuid)

    @classmethod
    def create_object(cls, type_name: str, props: dict[str, Any] | None = None) -> ObjectView:
        normalized = cls._normalize_props(type_name, props or {})
        klass = WTypeMeta.python_class(type_name)
        if klass is not None:
            instance_uuid = klass(**normalized).uuid
        else:
            instance_uuid = cls._create_db_only(type_name, normalized)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    def update_object(cls, uuid: UUID, props: dict[str, Any]) -> ObjectView:
        wrapper = WObject.wrap(uuid)
        with sessions.new() as session:
            type_name = cls._type_name_of(session, uuid)
        normalized = cls._normalize_props(type_name, props)
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    @classmethod
    def delete_object(cls, uuid: UUID) -> bool:
        with sessions.new() as session:
            if session.get(Instances, uuid) is None:
                return False
        WObject.wrap(uuid).delete()
        return True

    # --- internals ---

    @classmethod
    def _normalize_props(cls, type_name: str, props: dict[str, Any]) -> dict[str, Any]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        with sessions.new() as session:
            owner = WType.by_name(session, type_name)
            if owner is None:
                raise KeyError(f"no type {type_name!r}")
            return {
                key: cls._normalize_value(session, value, cls._prop_type_name(session, owner, key))
                for key, value in props.items()
            }

    @classmethod
    def _prop_type_name(cls, session: Session, owner: WType, key: str) -> str:
        prop = owner.prop(session, key)
        if prop is None:
            raise KeyError(f"type {owner.name!r} has no prop {key!r}")
        return prop.value_type(session).name

    @classmethod
    def _normalize_value(cls, session: Session, value: Any, type_name: str) -> Any:
        if WScalar.by_type_name(type_name) is not None:
            return value
        if WType.is_array_name(type_name):
            element_name = WType.element_name(type_name)
            return [cls._normalize_value(session, item, element_name) for item in value]
        if isinstance(value, ObjectRef):
            return WObject.wrap(value.uuid)
        if isinstance(value, UUID):
            return WObject.wrap(value)
        return value  # WObject passes through; anything else fails in setattr

    @classmethod
    def _type_view(cls, session: Session, name: str) -> TypeView:
        owner = WType.by_name(session, name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        return TypeView(
            name=name,
            props=[
                PropView(key=prop.key, value_type=prop.value_type(session).name)
                for prop in owner.props(session)
            ],
        )

    @classmethod
    def _create_db_only(cls, type_name: str, props: dict[str, Any]) -> UUID:
        """Types with no registered python class: bare instance row, then
        writes through the generic WObject wrapper — same validation."""
        with sessions.new() as session, session.begin():
            owner = WType.by_name(session, type_name)
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
    def _object_view(cls, session: Session, uuid: UUID) -> ObjectView | None:
        inst = session.get(Instances, uuid)
        if inst is None:
            return None
        owner = WType.by_uuid(session, inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        wrapper = WObject.wrap(uuid)
        props = {
            prop.key: cls._render(session, getattr(wrapper, prop.key))
            for prop in owner.props(session)
        }
        return ObjectView(uuid=uuid, type_name=owner.name, props=props)

    @classmethod
    def _render(cls, session: Session, value: Any) -> Any:
        if isinstance(value, WObject):
            return ObjectRef(uuid=value.uuid, type_name=cls._type_name_of(session, value.uuid))
        if isinstance(value, list):
            return [cls._render(session, item) for item in value]
        return value

    @classmethod
    def _type_name_of(cls, session: Session, uuid: UUID) -> str:
        inst = session.get(Instances, uuid)
        if inst is None:
            return "<gone>"
        owner = WType.by_uuid(session, inst.type_uuid)
        return "<dangling>" if owner is None else owner.name
