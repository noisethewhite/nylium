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

from collections.abc import Callable, ItemsView
from typing import ClassVar, cast, override
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.tables import TABLE_ArrayValues, TABLE_FileValues, TABLE_Instances, TABLE_InstanceValues, instances
from nylium.objects.warray import WArray
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, ScalarTable, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta
from nylium.objects.wunit import WUnit

INSTANCE_NAME_FORMAT = "{type_name}:{short_uuid}"
SHORT_UUID_LENGTH = 8
PRIVATE_PREFIX = "_"


class WObject(metaclass=WTypeMeta):
    __abstract__: ClassVar[bool] = True

    _uuid: UUID

    @databasemethod(commit=True)
    def __init__(self, _uuid: UUID | None = None, **props: StoredValue) -> None:
        # plain assignment: __setattr__ routes "_" names to object.__setattr__,
        # and the checker gets to see _uuid initialized
        self._uuid = _uuid or uuid4()
        if _uuid is not None:
            return
        self._register()
        for key, value in props.items():
            setattr(self, key, value)

    @databasemethod(commit=True)
    def _register(self) -> None:
        owner = WType.ensure(type(self).__name__)
        instances.create(
            self._uuid,
            owner.uuid,
            INSTANCE_NAME_FORMAT.format(
                type_name=type(self).__name__,
                short_uuid=str(self._uuid)[:SHORT_UUID_LENGTH],
            ),
        )

    @classmethod
    @databasemethod(commit=True)
    def create_db_only(cls, type_name: str, props: dict[str, StoredValue]) -> UUID:
        """Types with no registered python class: bare instance row, then
        writes through the generic WObject wrapper — same validation."""
        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        instance_uuid = uuid4()
        instances.create(
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
    @databasemethod(commit=False)
    def get(cls, uuid: UUID) -> "WObject | None":
        inst = Database.session.get(TABLE_Instances, uuid)
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
    @databasemethod(commit=False)
    def wrap(cls, uuid: UUID) -> "WObject":
        inst = Database.session.get(TABLE_Instances, uuid)
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
    @databasemethod(commit=False)
    def fields(cls) -> dict[str, str]:
        """prop key -> value spec name, e.g. {'tags': 'Array<String>'}.
        ADR-0013: the effective schema — attached traits' props included,
        trait-bound values render as 'Any<TraitName>'."""
        owner = WType.by_name(cls.__name__)
        if owner is None:
            return {}
        return {
            prop.key: prop.value_spec_name()
            for prop in WProp.effective_for(owner)
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

    @databasemethod(commit=False)
    def _prop_and_type(self, key: str) -> tuple[WProp, str]:
        inst = Database.session.get(TABLE_Instances, self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = WProp.effective_by_key(owner, key)
        if prop is None:
            raise AttributeError(f"{owner.name} has no prop {key!r}")
        return prop, prop.value_spec_name()

    @databasemethod(commit=False)
    def __getattr__(self, key: str) -> StoredValue:
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            row = Database.session.get(scalar.TABLE, (self._uuid, prop.uuid))
            return None if row is None else scalar.from_storage(row.value)
        if WType.unit_param_of(value_type) is not None:
            return WUnit.read(self._uuid, prop, value_type)
        if WEnum.is_enum(value_type):
            return WEnum.read(self._uuid, prop)
        if WFile.is_file_type(value_type):
            return self._file_ref(prop)
        link = self._link(prop)
        if link is None:
            return None
        if WType.is_array_name(value_type):
            return WArray.read(link.uuid, WType.element_name(value_type))
        return WObject.wrap(link.uuid)

    @override
    @databasemethod(commit=True)
    def __setattr__(self, key: str, value: StoredValue) -> None:
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
            WUnit.write(self._uuid, prop, WUnit.validate(value_type, value))
        elif WEnum.is_enum(value_type):
            WEnum.write(self._uuid, prop, WEnum.validate(value_type, value))
        elif WType.is_array_name(value_type):
            WArray.write(
                self._uuid,
                prop,
                WType.element_name(value_type),
                cast(list[StoredValue], value),
            )
        elif prop.is_trait_bound:
            # ADR-0013: Any<TraitName> — a plain object link whose type
            # must carry the bound trait
            WTypeMeta.check_trait_link(prop.value_trait_name(), value)
            self._write_link(prop, cast("WObject", value))
        elif prop.value_type().is_embedded:
            # composition (ADR-0004): the value is an inline props draft,
            # the child is created lazily / updated / deleted on None
            WEmbedded.write(self._uuid, prop, value)
        elif WFile.is_file_type(value_type):
            # file-typed prop (ADR-0008): the value is a files.uuid, never
            # an object link — files aren't instances anymore
            if value is not None and not isinstance(value, UUID):
                raise TypeError(
                    f"{value_type} prop takes a files.uuid, got {type(value).__name__}"
                )
            self._write_file_ref(prop, value)
        else:
            WTypeMeta.check_link(value_type, value)
            self._write_link(prop, cast("WObject", value))
        self._touch()

    @override
    @databasemethod(commit=True)
    def __delattr__(self, key: str) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__delattr__(self, key)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            row = Database.session.get(scalar.TABLE, (self._uuid, prop.uuid))
            if row is not None:
                Database.session.delete(row)
                self._touch()
            return
        if WType.unit_param_of(value_type) is not None:
            WUnit.write(self._uuid, prop, None)
            self._touch()
            return
        if WEnum.is_enum(value_type):
            WEnum.write(self._uuid, prop, None)
            self._touch()
            return
        if WFile.is_file_type(value_type):
            self._write_file_ref(prop, None)
            self._touch()
            return
        link = self._link(prop)
        if link is None:
            return
        if WType.is_array_name(value_type):
            WArray.destroy( link.uuid)
        elif not prop.is_trait_bound and prop.value_type().is_embedded:
            WEmbedded.destroy(link.uuid)  # the child dies with the prop
        else:
            Database.session.delete(link)
        self._touch()

    @databasemethod(commit=True)
    def _touch(self, ) -> None:
        _ = Database.session.execute(
            sqla.update(TABLE_Instances)
            .where(TABLE_Instances.uuid == self._uuid)
            .values(modified_at=sqla.func.now())
        )

    # --- reads ---

    @databasemethod(commit=False)
    def _link(self, prop: WProp) -> TABLE_InstanceValues | None:
        return Database.session.scalar(
            sqla.select(TABLE_InstanceValues).where(
                TABLE_InstanceValues.inst_uuid == self._uuid,
                TABLE_InstanceValues.prop_uuid == prop.uuid,
            )
        )

    @databasemethod(commit=False)
    def _file_ref(self, prop: WProp) -> UUID | None:
        return Database.session.scalar(
            sqla.select(TABLE_FileValues.file_uuid).where(
                TABLE_FileValues.inst_uuid == self._uuid,
                TABLE_FileValues.prop_uuid == prop.uuid,
            )
        )

    # --- writes ---

    @databasemethod(commit=True)
    def _write_scalar(
        self,
        prop: WProp,
        scalar: type[WScalar],
        value: ScalarPayload | None,
    ) -> None:
        table = scalar.TABLE
        row = Database.session.get(table, (self._uuid, prop.uuid))
        if value is None:
            # clearing a scalar removes the row — a NULL row violates the
            # table's NOT NULL constraint and reads back as None anyway
            if row is not None:
                Database.session.delete(row)
            return
        stored = scalar.to_storage(value)
        if row is None:
            ctor = cast("Callable[..., ScalarTable]", table)
            Database.session.add(ctor(inst_uuid=self._uuid, prop_uuid=prop.uuid, value=stored))
            return
        _ = Database.session.execute(
            sqla.update(table)
            .where(table.inst_uuid == self._uuid, table.prop_uuid == prop.uuid)
            .values(value=stored)
        )

    @databasemethod(commit=False)
    def _write_link(self, prop: WProp, value: "WObject") -> None:
        _ = Database.session.merge(
            TABLE_InstanceValues(uuid=value._uuid, prop_uuid=prop.uuid, inst_uuid=self._uuid)
        )

    @databasemethod(commit=True)
    def _write_file_ref(self, prop: WProp, value: UUID | None) -> None:
        if value is None:
            _ = Database.session.execute(
                sqla.delete(TABLE_FileValues).where(
                    TABLE_FileValues.inst_uuid == self._uuid,
                    TABLE_FileValues.prop_uuid == prop.uuid,
                )
            )
            return
        row = Database.session.get(TABLE_FileValues, (self._uuid, prop.uuid))
        if row is None:
            Database.session.add(
                TABLE_FileValues(file_uuid=value, prop_uuid=prop.uuid, inst_uuid=self._uuid)
            )
        else:
            row.file_uuid = value

    @databasemethod(commit=True)
    def delete(self, ) -> None:
        for array_uuid in self._owned_array_uuids():
            WArray.destroy(array_uuid)
        for child_uuid in self._owned_embedded_uuids():
            WEmbedded.destroy(child_uuid)
        _ = Database.session.execute(
            sqla.delete(TABLE_InstanceValues).where(TABLE_InstanceValues.uuid == self._uuid)
        )
        _ = Database.session.execute(
            sqla.delete(TABLE_ArrayValues).where(TABLE_ArrayValues.value_uuid == self._uuid)
        )
        inst = Database.session.get(TABLE_Instances, self._uuid)
        if inst is not None:
            Database.session.delete(inst)

    @databasemethod(commit=False)
    def _owned_embedded_uuids(self, ) -> list[UUID]:
        """TABLE_Instances held through embedded-typed props — composition
        children (ADR-0004), found via the owner_* read-index."""
        return list(
            Database.session.scalars(
                sqla.select(TABLE_Instances.uuid).where(
                    TABLE_Instances.owner_object_uuid == self._uuid
                )
            ).all()
        )

    @databasemethod(commit=False)
    def _owned_array_uuids(self, ) -> list[UUID]:
        from nylium.tables import TABLE_Props
        from nylium.tables.objects.types import TABLE_Types

        return list(
            Database.session.scalars(
                sqla.select(TABLE_InstanceValues.uuid)
                .join(TABLE_Props, TABLE_InstanceValues.prop_uuid == TABLE_Props.uuid)
                .join(TABLE_Types, TABLE_Props.value_type_uuid == TABLE_Types.uuid)
                .where(
                    TABLE_InstanceValues.inst_uuid == self._uuid,
                    TABLE_Types.name.like(WType.ARRAY_TYPE_PREFIX + "%"),
                )
            ).all()
        )
