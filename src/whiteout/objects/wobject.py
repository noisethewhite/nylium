"""WObject: an instance of a whiteout type, backed by the tables.py graph.

Subclass it with WScalar/WObject/list[...] annotations; the metaclass
materializes the type and its props in the database. Attribute
reads/writes translate into queries/upserts against the *values tables:

    class Person(WObject):
        name: WString
        friend: "Person"
        tags: list[WString]

    oleg = Person(name="Oleg")
    oleg.friend = maxim   # -> instance_values row, type-checked
    oleg.tags = ["a"]     # -> array instance + array_values rows

Session-per-operation on purpose: this is the correctness layer, not the
performance one.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.tables import ArrayValues, Instances, InstanceValues
from whiteout.objects.sessions import sessions
from whiteout.objects.warray import WArray
from whiteout.objects.wprop import WProp
from whiteout.objects.wscalar import WScalar
from whiteout.objects.wtype import WType
from whiteout.objects.wtypemeta import WTypeMeta

INSTANCE_NAME_FORMAT = "{type_name}:{short_uuid}"
SHORT_UUID_LENGTH = 8
PRIVATE_PREFIX = "_"


class WObject(metaclass=WTypeMeta):
    __abstract__ = True

    _uuid: UUID

    def __init__(self, _uuid: UUID | None = None, **props):
        object.__setattr__(self, "_uuid", _uuid or uuid4())
        if _uuid is not None:
            return
        with sessions.new() as session, session.begin():
            owner = WType.ensure(session, type(self).__name__)
            session.add(
                Instances(
                    uuid=self._uuid,
                    type_uuid=owner.uuid,
                    name=INSTANCE_NAME_FORMAT.format(
                        type_name=type(self).__name__,
                        short_uuid=str(self._uuid)[:SHORT_UUID_LENGTH],
                    ),
                )
            )
        for key, value in props.items():
            setattr(self, key, value)

    # --- retrieval ---

    @classmethod
    def get(cls, uuid: UUID) -> "WObject | None":
        with sessions.new() as session:
            inst = session.get(Instances, uuid)
            if inst is None:
                return None
            owner = WType.by_uuid(session, inst.type_uuid)
            if owner is None:
                raise RuntimeError(f"instance {uuid} has dangling type")
            actual_name = owner.name
        if cls is WObject:
            return cls(_uuid=uuid)
        actual_cls = WTypeMeta.python_class(actual_name)
        if actual_cls is not None and issubclass(actual_cls, cls):
            return cls(_uuid=uuid)
        if actual_cls is None and actual_name == cls.__name__:
            return cls(_uuid=uuid)
        raise TypeError(f"instance {uuid} is {actual_name}, not {cls.__name__}")

    @classmethod
    def wrap(cls, uuid: UUID) -> "WObject":
        with sessions.new() as session:
            inst = session.get(Instances, uuid)
            if inst is None:
                raise KeyError(f"no instance {uuid}")
            owner = WType.by_uuid(session, inst.type_uuid)
            if owner is None:
                raise KeyError(f"instance {uuid} has dangling type {inst.type_uuid}")
            type_name = owner.name
        klass = WTypeMeta.python_class(type_name) or WObject
        wrapped = klass.__new__(klass)
        object.__setattr__(wrapped, "_uuid", uuid)
        return wrapped

    @property
    def uuid(self) -> UUID:
        return self._uuid

    # --- dataclass-like facade for UI rendering ---

    @classmethod
    def fields(cls) -> dict[str, str]:
        """prop key -> value type name, e.g. {'tags': 'Array<String>'}"""
        with sessions.new() as session:
            owner = WType.by_name(session, cls.__name__)
            if owner is None:
                return {}
            return {
                prop.key: prop.value_type(session).name for prop in owner.props(session)
            }

    def to_dict(self) -> dict[str, object]:
        """Snapshot of all props. Links come back as WObject, arrays as lists."""
        return {key: getattr(self, key) for key in type(self).fields()}

    def items(self):
        return self.to_dict().items()

    def __repr__(self) -> str:
        try:
            parts = ", ".join(
                f"{key}={getattr(self, key)!r}" for key in type(self).fields()
            )
        except AttributeError:
            return f"<{type(self).__name__} {self._uuid} (gone)>"
        return f"{type(self).__name__}({parts})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WObject):
            return NotImplemented
        return self._uuid == other._uuid

    def __hash__(self) -> int:
        return hash(self._uuid)

    # --- attribute machinery ---

    def _prop_and_type(self, session: Session, key: str) -> tuple[WProp, str]:
        inst = session.get(Instances, self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        owner = WType.by_uuid(session, inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = owner.prop(session, key)
        if prop is None:
            raise AttributeError(f"{owner.name} has no prop {key!r}")
        return prop, prop.value_type(session).name

    def __getattr__(self, key: str):
        with sessions.new() as session:
            prop, value_type = self._prop_and_type(session, key)
            scalar = WScalar.by_type_name(value_type)
            if scalar is not None:
                row = session.get(scalar.TABLE, (self._uuid, prop.uuid))
                return None if row is None else row.value
            link = self._link(session, prop)
            if link is None:
                return None
            if WType.is_array_name(value_type):
                return WArray.read(session, link.uuid, WType.element_name(value_type))
            return WObject.wrap(link.uuid)

    def __setattr__(self, key: str, value) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__setattr__(self, key, value)
            return
        with sessions.new() as session, session.begin():
            prop, value_type = self._prop_and_type(session, key)
            scalar = WScalar.by_type_name(value_type)
            if scalar is not None:
                WScalar.validate(value_type, value)
                self._write_scalar(session, prop, scalar.TABLE, value)
            elif WType.is_array_name(value_type):
                WArray.write(session, self._uuid, prop, WType.element_name(value_type), value)
            else:
                WTypeMeta.check_link(session, value_type, value)
                self._write_link(session, prop, value)
            self._touch(session)

    def __delattr__(self, key: str) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__delattr__(self, key)
            return
        with sessions.new() as session, session.begin():
            prop, value_type = self._prop_and_type(session, key)
            scalar = WScalar.by_type_name(value_type)
            if scalar is not None:
                row = session.get(scalar.TABLE, (self._uuid, prop.uuid))
                if row is not None:
                    session.delete(row)
                    self._touch(session)
                return
            link = self._link(session, prop)
            if link is None:
                return
            if WType.is_array_name(value_type):
                WArray.destroy(session, link.uuid)
            else:
                session.delete(link)
            self._touch(session)

    def _touch(self, session: Session) -> None:
        session.execute(
            sqla.update(Instances)
            .where(Instances.uuid == self._uuid)
            .values(modified_at=sqla.func.now())
        )

    # --- reads ---

    def _link(self, session: Session, prop: WProp) -> InstanceValues | None:
        return session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == self._uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )

    # --- writes ---

    def _write_scalar(self, session: Session, prop: WProp, table, value) -> None:
        row = session.get(table, (self._uuid, prop.uuid))
        if row is None:
            session.add(table(inst_uuid=self._uuid, prop_uuid=prop.uuid, value=value))
            return
        row.value = value

    def _write_link(self, session: Session, prop: WProp, value: "WObject") -> None:
        session.merge(
            InstanceValues(uuid=value._uuid, prop_uuid=prop.uuid, inst_uuid=self._uuid)
        )

    def delete(self) -> None:
        with sessions.new() as session, session.begin():
            for array_uuid in self._owned_array_uuids(session):
                WArray.destroy(session, array_uuid)
            session.execute(
                sqla.delete(InstanceValues).where(InstanceValues.uuid == self._uuid)
            )
            session.execute(
                sqla.delete(ArrayValues).where(ArrayValues.value_uuid == self._uuid)
            )
            inst = session.get(Instances, self._uuid)
            if inst is not None:
                session.delete(inst)

    def _owned_array_uuids(self, session: Session) -> list[UUID]:
        from whiteout.database.tables import Props, Types

        return list(
            session.scalars(
                sqla.select(InstanceValues.uuid)
                .join(Props, InstanceValues.prop_uuid == Props.uuid)
                .join(Types, Props.value_type_uuid == Types.uuid)
                .where(
                    InstanceValues.inst_uuid == self._uuid,
                    Types.name.like(WType.ARRAY_TYPE_PREFIX + "%"),
                )
            ).all()
        )
