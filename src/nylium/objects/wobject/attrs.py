"""WObject attribute machinery: __getattr__/__setattr__/__delattr__
dispatch over prop value kinds (scalar, unit, enum, file, array, link,
trait-bound, embedded) plus _prop_and_type resolution and _touch.

ADR-0019: statements live in ``nylium.tables`` — no ``sqla`` / ``Database``
imports here.
"""
from __future__ import annotations

from typing import cast, override
from uuid import UUID

from nylium.database import Database
from nylium.objects.tables.instances import get as get_instance_row
from nylium.objects.tables.instances import touch as touch_instance
from nylium.tables.values import cells, instance_values
from nylium.objects.warray import WArray
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WObjectShape, WTypeMeta
from nylium.objects.wunit import WUnit
from nylium.objects.wobject.constants import PRIVATE_PREFIX
from nylium.objects.wobject.persistence import PersistenceMixin


class AttrsMixin(PersistenceMixin):
    # --- attribute machinery ---

    @Database.use_same_session
    def _prop_and_type(self, key: str) -> tuple[WProp, str]:
        inst = get_instance_row(self._uuid)
        if inst is None:
            raise AttributeError(f"instance {self._uuid} does not exist")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {self._uuid} has dangling type")
        prop = WProp.effective_by_key(owner, key)
        if prop is None:
            raise AttributeError(f"{owner.name} has no prop {key!r}")
        return prop, prop.value_spec_name()

    @Database.use_same_session
    def __getattr__(self, key: str) -> StoredValue:
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            stored = cells.read(scalar.TABLE, self._uuid, prop.uuid)
            return None if stored is None else scalar.from_storage(stored)
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
        return WTypeMeta.root().wrap(link.uuid)

    @override
    @Database.commit_after_this
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
                cast(list[StoredValue] | None, value),
            )
        elif prop.is_trait_bound:
            # ADR-0013: Any<TraitName> — a plain object link whose type
            # must carry the bound trait
            WTypeMeta.check_trait_link(prop.value_trait_name(), value)
            self._write_link(prop, cast(WObjectShape, value))
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
            self._write_link(prop, cast(WObjectShape, value))
        self._touch()

    @override
    @Database.commit_after_this
    def __delattr__(self, key: str) -> None:
        if key.startswith(PRIVATE_PREFIX):
            object.__delattr__(self, key)
            return
        prop, value_type = self._prop_and_type(key)
        scalar = WScalar.by_type_name(value_type)
        if scalar is not None:
            if cells.clear(scalar.TABLE, self._uuid, prop.uuid):
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
            WArray.destroy(link.uuid)
        elif not prop.is_trait_bound and prop.value_type().is_embedded:
            WEmbedded.destroy(link.uuid)  # the child dies with the prop
        else:
            instance_values.delete_row(link)
        self._touch()

    @Database.commit_after_this
    def _touch(self) -> None:
        touch_instance(self._uuid)
