"""NyObject attribute machinery: __getattr__/__setattr__/__delattr__
dispatch over prop value kinds (scalar, unit, enum, file, array, link,
trait-bound, embedded) plus _prop_and_type resolution and _touch.

ADR-0019 / ADR-0030: statements live in the ``nylium.objects`` helpers
(wlink) — no ``sqla`` / ``Database`` imports here.
"""
from __future__ import annotations

from typing import cast, override
from uuid import UUID

from nylium.database import Database
from nylium.data.tables import Instances, instances
from nylium.data.tables import InstanceValues
from nylium.objects.NyArray import NyArray
from nylium.objects.NyEmbedded import NyEmbedded
from nylium.objects.NyEnum import NyEnum
from nylium.objects.NyFile import NyFile
from nylium.objects.NyProp import NyProp
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyScalar import ScalarPayload
from nylium.objects.NyType import NyType
from nylium.objects.NyObjectShape import NyObjectShape
from nylium.objects.NyTypeMeta import StoredValue, NyTypeMeta
from nylium.objects.NyUnit import NyUnit
from nylium.objects.nyobject.constants import PRIVATE_PREFIX
from nylium.objects.nyobject.PersistenceMixin import PersistenceMixin


class AttrsMixin(PersistenceMixin):
    # --- attribute machinery ---

    @Database.use_same_session
    def _prop_and_type(self, key: str) -> tuple[NyProp, str]:
        inst = instances.get(self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        owner = NyType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = NyProp.effective_by_key(owner, key)
        if prop is None:
            raise AttributeError(f"{owner.name} has no prop {key!r}")
        return prop, prop.value_spec_name()

    @Database.use_same_session
    def __getattr__(self, key: str) -> StoredValue:
        prop, value_type = self._prop_and_type(key)
        scalar = NyScalar.by_type_name(value_type)
        if scalar is not None:
            stored = scalar.SCALAR.read(self._uuid, prop.uuid)
            return None if stored is None else scalar.from_storage(stored)
        if NyType.unit_param_of(value_type) is not None:
            return NyUnit.read(self._uuid, prop, value_type)
        if NyEnum.is_enum(value_type):
            return NyEnum.read(self._uuid, prop)
        if NyFile.is_file_type(value_type):
            return self._file_ref(prop)
        link = self._link(prop)
        if link is None:
            return None
        if NyType.is_array_name(value_type):
            return NyArray.read(link.uuid, NyType.element_name(value_type))
        return NyTypeMeta.root().wrap(link.uuid)

    @override
    @Database.commit_after_this
    def __setattr__(self, key: str, value: StoredValue) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__setattr__(self, key, value)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = NyScalar.by_type_name(value_type)
        if scalar is not None:
            payload = cast(ScalarPayload | None, value)
            NyScalar.validate(value_type, payload)
            self._write_scalar(prop, scalar, payload)
        elif NyType.unit_param_of(value_type) is not None:
            NyUnit.write(self._uuid, prop, NyUnit.validate(value_type, value))
        elif NyEnum.is_enum(value_type):
            NyEnum.write(self._uuid, prop, NyEnum.validate(value_type, value))
        elif NyType.is_array_name(value_type):
            NyArray.write(
                self._uuid,
                prop,
                NyType.element_name(value_type),
                cast(list[StoredValue] | None, value),
            )
        elif prop.is_trait_bound:
            # ADR-0013: Any<TraitName> — a plain object link whose type
            # must carry the bound trait
            NyTypeMeta.check_trait_link(prop.value_trait_name(), value)
            self._write_link(prop, cast(NyObjectShape, value))
        elif prop.value_type().is_embedded:
            # composition (ADR-0004): the value is an inline props draft,
            # the child is created lazily / updated / deleted on None
            NyEmbedded.write(self._uuid, prop, value)
        elif NyFile.is_file_type(value_type):
            # file-typed prop (ADR-0008): the value is a files.uuid, never
            # an object link — files aren't instances anymore
            if value is not None and not isinstance(value, UUID):
                raise TypeError(
                    f"{value_type} prop takes a files.uuid, got {type(value).__name__}"
                )
            self._write_file_ref(prop, value)
        else:
            NyTypeMeta.check_link(value_type, value)
            self._write_link(prop, cast(NyObjectShape, value))
        self._touch()

    @override
    @Database.commit_after_this
    def __delattr__(self, key: str) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__delattr__(self, key)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = NyScalar.by_type_name(value_type)
        if scalar is not None:
            if scalar.SCALAR.clear(self._uuid, prop.uuid):
                self._touch()
            return
        if NyType.unit_param_of(value_type) is not None:
            NyUnit.write(self._uuid, prop, None)
            self._touch()
            return
        if NyEnum.is_enum(value_type):
            NyEnum.write(self._uuid, prop, None)
            self._touch()
            return
        if NyFile.is_file_type(value_type):
            self._write_file_ref(prop, None)
            self._touch()
            return
        link = self._link(prop)
        if link is None:
            return
        if NyType.is_array_name(value_type):
            NyArray.destroy(link.uuid)
        elif not prop.is_trait_bound and prop.value_type().is_embedded:
            NyEmbedded.destroy(link.uuid)  # the child dies with the prop
        else:
            InstanceValues.delete_row(link)
        self._touch()

    @Database.commit_after_this
    def _touch(self) -> None:
        Instances.touch(self._uuid)
