"""WObject: an instance of a nylium type, backed by the tables.py graph.

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

from collections.abc import ItemsView
from typing import ClassVar, cast, override
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database
from nylium.database.tables import ArrayValues, Instances, InstanceValues
from nylium.objects.warray import WArray
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wenum import WEnum
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta
from nylium.objects.wunit import WUnit

INSTANCE_NAME_FORMAT = "{type_name}:{short_uuid}"
SHORT_UUID_LENGTH = 8
PRIVATE_PREFIX = "_"


class WObject(metaclass=WTypeMeta):
    __abstract__: ClassVar[bool] = True

    _uuid: UUID

    @Database.sessionmethod(bundled=True, commit=True)
    def __init__(self, _uuid: UUID | None = None, **props: StoredValue) -> None:
        # plain assignment: __setattr__ routes "_" names to object.__setattr__,
        # and the checker gets to see _uuid initialized
        self._uuid = _uuid or uuid4()
        if _uuid is not None:
            return
        self._register()
        for key, value in props.items():
            setattr(self, key, value)

    @Database.sessionmethod(bundled=True, commit=True)
    def _register(self) -> None:
        owner = WType.ensure(type(self).__name__)
        Instances.register(
            self._uuid,
            owner.uuid,
            INSTANCE_NAME_FORMAT.format(
                type_name=type(self).__name__,
                short_uuid=str(self._uuid)[:SHORT_UUID_LENGTH],
            ),
        )

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_db_only(cls, type_name: str, props: dict[str, StoredValue]) -> UUID:
        """Types with no registered python class: bare instance row, then
        writes through the generic WObject wrapper — same validation."""
        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        instance_uuid = uuid4()
        Instances.register(
            instance_uuid,
            owner.uuid,
            INSTANCE_NAME_FORMAT.format(
                type_name=type_name,
                short_uuid=str(instance_uuid)[:SHORT_UUID_LENGTH],
            ),
        )
        wrapper = cls.wrap(instance_uuid)
        for key, value in props.items():
            setattr(wrapper, key, value)
        return instance_uuid

    # --- retrieval ---

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get(cls, session: Session, uuid: UUID) -> "WObject | None":
        inst = session.get(Instances, uuid)
        if inst is None:
            return None
        owner = WType.by_uuid(inst.type_uuid)
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
    @Database.sessionmethod(bundled=False, commit=False)
    def wrap(cls, session: Session, uuid: UUID) -> "WObject":
        inst = session.get(Instances, uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise KeyError(f"instance {uuid} has dangling type {inst.type_uuid}")
        klass = WTypeMeta.python_class(owner.name) or WObject
        wrapped = klass.__new__(klass)
        object.__setattr__(wrapped, "_uuid", uuid)
        return cast("WObject", wrapped)

    @property
    def uuid(self) -> UUID:
        return self._uuid

    # --- dataclass-like facade for UI rendering ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def fields(cls) -> dict[str, str]:
        """prop key -> value type name, e.g. {'tags': 'Array<String>'}"""
        owner = WType.by_name(cls.__name__)
        if owner is None:
            return {}
        return {
            prop.key: prop.value_type().name
            for prop in WProp.all_for(owner)
        }

    def to_dict(self) -> dict[str, StoredValue]:
        """Snapshot of all props. Links come back as WObject, arrays as lists."""
        return {key: cast(StoredValue, getattr(self, key)) for key in type(self).fields()}

    def items(self) -> ItemsView[str, StoredValue]:
        return self.to_dict().items()

    @override
    def __repr__(self) -> str:
        try:
            parts = ", ".join(
                f"{key}={getattr(self, key)!r}" for key in type(self).fields()
            )
        except AttributeError:
            return f"<{type(self).__name__} {self._uuid} (gone)>"
        return f"{type(self).__name__}({parts})"

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WObject):
            return NotImplemented
        return self._uuid == other._uuid

    @override
    def __hash__(self) -> int:
        return hash(self._uuid)

    # --- attribute machinery ---

    @Database.sessionmethod(bundled=False, commit=False)
    def _prop_and_type(self, session: Session, key: str) -> tuple[WProp, str]:
        inst = session.get(Instances, self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = WProp.by_key(owner, key)
        if prop is None:
            raise AttributeError(f"{owner.name} has no prop {key!r}")
        return prop, prop.value_type().name

    @Database.sessionmethod(bundled=False, commit=False)
    def __getattr__(self, session: Session, key: str) -> StoredValue:
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            row = session.get(scalar.TABLE, (self._uuid, prop.uuid))
            return None if row is None else scalar.from_storage(row.value)
        if WType.unit_param_of(value_type) is not None:
            return WUnit.read(session, self._uuid, prop, value_type)
        if WEnum.is_enum(value_type):
            return WEnum.read(session, self._uuid, prop)
        link = self._link(prop)
        if link is None:
            return None
        if WType.is_array_name(value_type):
            return WArray.read(link.uuid, WType.element_name(value_type))
        return WObject.wrap(link.uuid)

    @override
    @Database.sessionmethod(bundled=False, commit=True)
    def __setattr__(self, session: Session, key: str, value: StoredValue) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__setattr__(self, key, value)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            payload = cast(ScalarPayload | None, value)
            WScalar.validate(value_type, payload)
            self._write_scalar(prop, scalar, payload)
        elif WType.unit_param_of(value_type) is not None:
            WUnit.write(session, self._uuid, prop, WUnit.validate(value_type, value))
        elif WEnum.is_enum(value_type):
            WEnum.write(session, self._uuid, prop, WEnum.validate(value_type, value))
        elif WType.is_array_name(value_type):
            WArray.write(
                self._uuid,
                prop,
                WType.element_name(value_type),
                cast(list[StoredValue], value),
            )
        elif prop.value_type().is_embedded:
            # composition (ADR-0004): the value is an inline props draft,
            # the child is created lazily / updated / deleted on None
            WEmbedded.write(self._uuid, prop, value)
        else:
            WTypeMeta.check_link(value_type, value)
            self._write_link(prop, cast("WObject", value))
        self._touch()

    @override
    @Database.sessionmethod(bundled=False, commit=True)
    def __delattr__(self, session: Session, key: str) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__delattr__(self, key)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            row = session.get(scalar.TABLE, (self._uuid, prop.uuid))
            if row is not None:
                session.delete(row)
                self._touch()
            return
        if WType.unit_param_of(value_type) is not None:
            WUnit.write(session, self._uuid, prop, None)
            self._touch()
            return
        if WEnum.is_enum(value_type):
            WEnum.write(session, self._uuid, prop, None)
            self._touch()
            return
        link = self._link(prop)
        if link is None:
            return
        if WType.is_array_name(value_type):
            WArray.destroy( link.uuid)
        elif prop.value_type().is_embedded:
            WEmbedded.destroy(link.uuid)  # the child dies with the prop
        else:
            session.delete(link)
        self._touch()

    @Database.sessionmethod(bundled=False, commit=True)
    def _touch(self, session: Session) -> None:
        _ = session.execute(
            sqla.update(Instances)
            .where(Instances.uuid == self._uuid)
            .values(modified_at=sqla.func.now())
        )

    # --- reads ---

    @Database.sessionmethod(bundled=False, commit=False)
    def _link(self, session: Session, prop: WProp) -> InstanceValues | None:
        return session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == self._uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )

    # --- writes ---

    @Database.sessionmethod(bundled=False, commit=True)
    def _write_scalar(
        self,
        session: Session,
        prop: WProp,
        scalar: type[WScalar],
        value: ScalarPayload | None,
    ) -> None:
        table = scalar.TABLE
        stored = None if value is None else scalar.to_storage(value)
        row = session.get(table, (self._uuid, prop.uuid))
        if row is None:
            session.add(table(inst_uuid=self._uuid, prop_uuid=prop.uuid, value=stored))
            return
        _ = session.execute(
            sqla.update(table)
            .where(table.inst_uuid == self._uuid, table.prop_uuid == prop.uuid)
            .values(value=stored)
        )

    @Database.sessionmethod(bundled=False, commit=False)
    def _write_link(self, session: Session, prop: WProp, value: "WObject") -> None:
        _ = session.merge(
            InstanceValues(uuid=value._uuid, prop_uuid=prop.uuid, inst_uuid=self._uuid)
        )

    @Database.sessionmethod(bundled=False, commit=True)
    def delete(self, session: Session) -> None:
        for array_uuid in self._owned_array_uuids():
            WArray.destroy(array_uuid)
        for child_uuid in self._owned_embedded_uuids():
            WEmbedded.destroy(child_uuid)
        _ = session.execute(
            sqla.delete(InstanceValues).where(InstanceValues.uuid == self._uuid)
        )
        _ = session.execute(
            sqla.delete(ArrayValues).where(ArrayValues.value_uuid == self._uuid)
        )
        inst = session.get(Instances, self._uuid)
        if inst is not None:
            session.delete(inst)

    @Database.sessionmethod(bundled=False, commit=False)
    def _owned_embedded_uuids(self, session: Session) -> list[UUID]:
        """Instances held through embedded-typed props — composition
        children (ADR-0004), found via the owner_* read-index."""
        return list(
            session.scalars(
                sqla.select(Instances.uuid).where(
                    Instances.owner_object_uuid == self._uuid
                )
            ).all()
        )

    @Database.sessionmethod(bundled=False, commit=False)
    def _owned_array_uuids(self, session: Session) -> list[UUID]:
        from nylium.database.tables import Props, Types

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
