"""Dynamic object layer over tables.py.

A subclass of WObject with plain annotations materializes a Types row plus
Props rows in the database at class-definition time. Attribute access on
instances then translates into queries/upserts against the *values tables:

    class Person(WObject):
        name: str
        friend: "Person"
        tags: list[str]

    p = Person(name="Max")
    p.friend = other      # -> instance_values row
    p.tags = ["a", "b"]   # -> array instance + array_values rows

Scalar types ("String", "Integer", ...) live in `types` like any other type,
so props.value_type_uuid stays one honest FK. Scalars used as array elements
or link values are boxed: an Instances row of the scalar type whose canonical
"value" prop holds the payload in the matching *values table.

Session-per-operation on purpose: this is the correctness sketch, not the
performance one.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import cast, get_args, get_origin
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.database import Database
from whiteout.database.tables import (
    ArrayValues,
    BooleanValues,
    DatetimeValues,
    Instances,
    InstanceValues,
    IntegerValues,
    NumericValues,
    Props,
    StringValues,
    Types,
)

VALUE_PROP = "value"

SCALAR_TABLES = {
    "String": StringValues,
    "Integer": IntegerValues,
    "Numeric": NumericValues,
    "Boolean": BooleanValues,
    "Datetime": DatetimeValues,
}

_ANNOTATION_NAMES = {
    "str": "String",
    "int": "Integer",
    "Decimal": "Numeric",
    "bool": "Boolean",
    "datetime": "Datetime",
}

_TYPE_CLASSES: dict[str, type["WObject"]] = {}


def _session() -> Session:
    return Session(Database().engine)


def _annotation_type_name(annotation: object) -> str:
    if isinstance(annotation, str):
        name = annotation.strip().strip("\"'")
        if name.startswith("list[") and name.endswith("]"):
            return f"Array<{_annotation_type_name(name[5:-1])}>"
        return _ANNOTATION_NAMES.get(name, name)
    if get_origin(annotation) is list:
        return f"Array<{_annotation_type_name(get_args(annotation)[0])}>"
    for py_type, name in _SCALAR_PY_TYPES.items():
        if annotation is py_type:
            return name
    if isinstance(annotation, type) and issubclass(annotation, WObject):
        return annotation.__name__
    raise TypeError(f"unsupported annotation: {annotation!r}")


_SCALAR_PY_TYPES = {
    str: "String",
    int: "Integer",
    Decimal: "Numeric",
    bool: "Boolean",
    datetime: "Datetime",
}


def _ensure_type(session: Session, name: str) -> Types:
    row = session.scalar(sqla.select(Types).where(Types.name == name))
    if row is not None:
        return row
    row = Types(uuid=uuid4(), name=name)
    session.add(row)
    session.flush()
    return row


def _ensure_scalar_value_prop(session: Session, type_row: Types) -> None:
    exists = session.scalar(
        sqla.select(Props).where(
            Props.owner_type_uuid == type_row.uuid, Props.key == VALUE_PROP
        )
    )
    if exists is not None:
        return
    session.add(
        Props(
            uuid=uuid4(),
            key=VALUE_PROP,
            owner_type_uuid=type_row.uuid,
            value_type_uuid=type_row.uuid,
        )
    )


def ensure_builtin_types() -> None:
    with _session() as session, session.begin():
        for name in SCALAR_TABLES:
            _ensure_scalar_value_prop(session, _ensure_type(session, name))


class WTypeMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        if namespace.get("__abstract__"):
            return cls
        typed_cls = cast(type["WObject"], cls)
        _TYPE_CLASSES[name] = typed_cls
        _materialize(typed_cls)
        return cls


def _materialize(cls: type["WObject"]) -> None:
    ensure_builtin_types()
    with _session() as session, session.begin():
        type_row = _ensure_type(session, cls.__name__)
        for key, annotation in getattr(cls, "__annotations__", {}).items():
            if key.startswith("_"):
                continue
            value_type_name = _annotation_type_name(annotation)
            value_type = _ensure_type(session, value_type_name)
            existing = session.scalar(
                sqla.select(Props).where(
                    Props.owner_type_uuid == type_row.uuid, Props.key == key
                )
            )
            if existing is not None:
                existing.value_type_uuid = value_type.uuid
                continue
            session.add(
                Props(
                    uuid=uuid4(),
                    key=key,
                    owner_type_uuid=type_row.uuid,
                    value_type_uuid=value_type.uuid,
                )
            )


class WObject(metaclass=WTypeMeta):
    __abstract__ = True

    _uuid: UUID

    def __init__(self, _uuid: UUID | None = None, **props):
        object.__setattr__(self, "_uuid", _uuid or uuid4())
        if _uuid is not None:
            return
        with _session() as session, session.begin():
            type_row = _ensure_type(session, type(self).__name__)
            session.add(
                Instances(
                    uuid=self._uuid,
                    type_uuid=type_row.uuid,
                    name=f"{type(self).__name__}:{str(self._uuid)[:8]}",
                )
            )
        for key, value in props.items():
            setattr(self, key, value)

    @classmethod
    def get(cls, uuid: UUID) -> "WObject | None":
        with _session() as session:
            if session.get(Instances, uuid) is None:
                return None
        return cls(_uuid=uuid)

    @classmethod
    def wrap(cls, uuid: UUID) -> "WObject":
        with _session() as session:
            inst = session.get(Instances, uuid)
            if inst is None:
                raise KeyError(f"no instance {uuid}")
            type_row = session.get(Types, inst.type_uuid)
            if type_row is None:
                raise KeyError(f"instance {uuid} has dangling type {inst.type_uuid}")
            type_name = type_row.name
        klass = _TYPE_CLASSES.get(type_name, WObject)
        wrapped = klass.__new__(klass)
        object.__setattr__(wrapped, "_uuid", uuid)
        return wrapped

    @property
    def uuid(self) -> UUID:
        return self._uuid

    # --- dataclass-like facade: enumerate and snapshot props for UI rendering ---

    @classmethod
    def fields(cls) -> dict[str, str]:
        """prop key -> value type name, e.g. {'name': 'String', 'tags': 'Array<String>'}"""
        with _session() as session:
            type_row = session.scalar(
                sqla.select(Types).where(Types.name == cls.__name__)
            )
            if type_row is None:
                return {}
            props = session.scalars(
                sqla.select(Props).where(Props.owner_type_uuid == type_row.uuid)
            ).all()
            result = {}
            for prop in props:
                value_type = session.get(Types, prop.value_type_uuid)
                if value_type is not None:
                    result[prop.key] = value_type.name
            return result

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

    def _prop_and_type(self, session: Session, key: str) -> tuple[Props, str]:
        inst = session.get(Instances, self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        type_row = session.get(Types, inst.type_uuid)
        if type_row is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = session.scalar(
            sqla.select(Props).where(
                Props.owner_type_uuid == type_row.uuid, Props.key == key
            )
        )
        if prop is None:
            raise AttributeError(f"{type_row.name} has no prop {key!r}")
        value_type_row = session.get(Types, prop.value_type_uuid)
        if value_type_row is None:
            raise RuntimeError(f"prop {key!r} has dangling value type")
        return prop, value_type_row.name

    def __getattr__(self, key: str):
        with _session() as session:
            prop, value_type = self._prop_and_type(session, key)
            if value_type in SCALAR_TABLES:
                row = session.get(SCALAR_TABLES[value_type], (self._uuid, prop.uuid))
                return None if row is None else row.value
            link = session.scalar(
                sqla.select(InstanceValues).where(
                    InstanceValues.inst_uuid == self._uuid,
                    InstanceValues.prop_uuid == prop.uuid,
                )
            )
            if link is None:
                return None
            if value_type.startswith("Array<"):
                return self._read_array(session, link.uuid, value_type[6:-1])
            return WObject.wrap(link.uuid)

    def _read_array(self, session: Session, array_uuid: UUID, elem_type: str):
        rows = session.scalars(
            sqla.select(ArrayValues)
            .where(ArrayValues.inst_uuid == array_uuid)
            .order_by(ArrayValues.index)
        ).all()
        return [self._unwrap(session, row.value_uuid, elem_type) for row in rows]

    def _unwrap(self, session: Session, uuid: UUID, type_name: str):
        if type_name not in SCALAR_TABLES:
            return WObject.wrap(uuid)
        inst = session.get(Instances, uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        prop = session.scalar(
            sqla.select(Props).where(
                Props.key == VALUE_PROP,
                Props.owner_type_uuid == inst.type_uuid,
            )
        )
        if prop is None:
            raise RuntimeError(f"scalar type {type_name} lost its {VALUE_PROP!r} prop")
        row = session.get(SCALAR_TABLES[type_name], (uuid, prop.uuid))
        return None if row is None else row.value

    def __setattr__(self, key: str, value) -> None:
        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return
        with _session() as session, session.begin():
            prop, value_type = self._prop_and_type(session, key)
            if value_type in SCALAR_TABLES:
                self._write_scalar(session, prop, SCALAR_TABLES[value_type], value)
                return
            if value_type.startswith("Array<"):
                self._write_array(session, prop, value_type[6:-1], value)
                return
            self._write_link(session, prop, value)

    def _write_scalar(self, session: Session, prop: Props, table, value) -> None:
        row = session.get(table, (self._uuid, prop.uuid))
        if row is None:
            session.add(table(inst_uuid=self._uuid, prop_uuid=prop.uuid, value=value))
            return
        row.value = value

    def _write_link(self, session: Session, prop: Props, value: "WObject") -> None:
        if not isinstance(value, WObject):
            raise TypeError(f"expected WObject, got {type(value)}")
        session.merge(
            InstanceValues(uuid=value._uuid, prop_uuid=prop.uuid, inst_uuid=self._uuid)
        )

    def _write_array(
        self, session: Session, prop: Props, elem_type: str, values: list
    ) -> None:
        if not isinstance(values, list):
            raise TypeError(f"expected list, got {type(values)}")
        link = session.scalar(
            sqla.select(InstanceValues).where(
                InstanceValues.inst_uuid == self._uuid,
                InstanceValues.prop_uuid == prop.uuid,
            )
        )
        array_uuid = link.uuid if link is not None else uuid4()
        if link is None:
            array_type = _ensure_type(session, f"Array<{elem_type}>")
            session.add(
                Instances(uuid=array_uuid, type_uuid=array_type.uuid, name="array")
            )
            session.flush()
            session.add(
                InstanceValues(
                    uuid=array_uuid, prop_uuid=prop.uuid, inst_uuid=self._uuid
                )
            )
        session.execute(
            sqla.delete(ArrayValues).where(ArrayValues.inst_uuid == array_uuid)
        )
        for index, item in enumerate(values):
            session.add(
                ArrayValues(
                    inst_uuid=array_uuid,
                    index=index,
                    value_uuid=self._box(session, elem_type, item),
                )
            )

    def _box(self, session: Session, type_name: str, value) -> UUID:
        if isinstance(value, WObject):
            return value._uuid
        box_uuid = uuid4()
        type_row = _ensure_type(session, type_name)
        session.add(Instances(uuid=box_uuid, type_uuid=type_row.uuid, name=str(value)))
        session.flush()
        if type_name in SCALAR_TABLES:
            value_prop = session.scalar(
                sqla.select(Props).where(
                    Props.owner_type_uuid == type_row.uuid, Props.key == VALUE_PROP
                )
            )
            if value_prop is None:
                raise RuntimeError(
                    f"scalar type {type_name} lost its {VALUE_PROP!r} prop"
                )
            session.add(
                SCALAR_TABLES[type_name](
                    inst_uuid=box_uuid, prop_uuid=value_prop.uuid, value=value
                )
            )
        return box_uuid

    def __delattr__(self, key: str) -> None:
        if key.startswith("_"):
            object.__delattr__(self, key)
            return
        with _session() as session, session.begin():
            prop, value_type = self._prop_and_type(session, key)
            if value_type in SCALAR_TABLES:
                row = session.get(SCALAR_TABLES[value_type], (self._uuid, prop.uuid))
                if row is not None:
                    session.delete(row)
                return
            session.execute(
                sqla.delete(InstanceValues).where(
                    InstanceValues.inst_uuid == self._uuid,
                    InstanceValues.prop_uuid == prop.uuid,
                )
            )

    def delete(self) -> None:
        with _session() as session, session.begin():
            session.execute(
                sqla.delete(InstanceValues).where(InstanceValues.uuid == self._uuid)
            )
            session.execute(
                sqla.delete(ArrayValues).where(ArrayValues.value_uuid == self._uuid)
            )
            inst = session.get(Instances, self._uuid)
            if inst is not None:
                session.delete(inst)
