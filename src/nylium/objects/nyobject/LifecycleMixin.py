"""NyObject lifecycle: construction, registration, retrieval (get/wrap),
uuid identity and the cascading delete.

ADR-0019 / ADR-0030: statements live in the ``nylium.objects`` helpers
(nyarray/wlink) — no ``sqla`` / ``Database`` imports here.
"""
from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from nylium.database import Database
from nylium.objects.navigation import array_link_uuids_of
from nylium.data.tables import Instances, instances
from nylium.data.tables import ArrayValues
from nylium.data.tables import InstanceValues
from nylium.objects.NyArray import NyArray
from nylium.objects.NyEmbedded import NyEmbedded
from nylium.objects.NyType import NyType
from nylium.objects.NyObjectShape import NyObjectShape
from nylium.objects.NyTypeMeta import StoredValue, NyTypeMeta
from nylium.objects.nyobject.constants import INSTANCE_NAME_FORMAT, SHORT_UUID_LENGTH


class LifecycleMixin:
    _uuid: UUID

    @Database.commit_after_this
    def __init__(self, _uuid: UUID | None = None, **props: StoredValue) -> None:
        # plain assignment: __setattr__ routes "_" names to object.__setattr__,
        # and the checker gets to see _uuid initialized
        self._uuid = _uuid or uuid4()
        if _uuid is not None:
            return
        self._register()
        for key, value in props.items():
            setattr(self, key, value)

    @Database.commit_after_this
    def _register(self) -> None:
        owner = NyType.ensure(type(self).__name__)
        instances.create(
            self._uuid,
            owner.uuid,
            INSTANCE_NAME_FORMAT.format(
                type_name=type(self).__name__,
                short_uuid=str(self._uuid)[:SHORT_UUID_LENGTH],
            ),
        )

    @classmethod
    @Database.commit_after_this
    def create_db_only(cls, type_name: str, props: dict[str, StoredValue]) -> UUID:
        """Types with no registered python class: bare instance row, then
        writes through the generic NyObject wrapper — same validation."""
        owner = NyType.by_name(type_name)
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
    @Database.use_same_session
    def get(cls, uuid: UUID) -> NyObjectShape | None:
        inst = instances.get(uuid)
        if inst is None:
            return None
        owner = NyType.by_uuid(inst.type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        actual_name = owner.name
        # cls is type[Self] of the mixin — the concrete class composes the
        # mixins into NyObject, hence the cast
        if cls is NyTypeMeta.root():
            return cast(NyObjectShape, cls(_uuid=uuid))
        actual_cls = NyTypeMeta.python_class(actual_name)
        if actual_cls is not None and issubclass(actual_cls, cls):
            return cast(NyObjectShape, cls(_uuid=uuid))
        if actual_cls is None and actual_name == cls.__name__:
            return cast(NyObjectShape, cls(_uuid=uuid))
        raise TypeError(f"instance {uuid} is {actual_name}, not {cls.__name__}")

    @classmethod
    @Database.use_same_session
    def wrap(cls, uuid: UUID) -> NyObjectShape:
        inst = instances.get(uuid)
        if inst is None:
            raise KeyError(f"no instance {uuid}")
        owner = NyType.by_uuid(inst.type_uuid)
        if owner is None:
            raise KeyError(f"instance {uuid} has dangling type {inst.type_uuid}")
        klass = NyTypeMeta.python_class(owner.name) or NyTypeMeta.root()
        wrapped = klass.__new__(klass)
        object.__setattr__(wrapped, "_uuid", uuid)
        return wrapped

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @Database.commit_after_this
    def delete(self) -> None:
        for array_uuid in self._owned_array_uuids():
            NyArray.destroy(array_uuid)
        for child_uuid in self._owned_embedded_uuids():
            NyEmbedded.destroy(child_uuid)
        InstanceValues.delete_links_to(self._uuid)
        ArrayValues.delete_memberships(self._uuid)
        Instances.delete_row(self._uuid)

    def _owned_embedded_uuids(self) -> list[UUID]:
        """Instance rows held through embedded-typed props — composition
        children (ADR-0004), found via the owner_* read-index."""
        return Instances.owned_uuids(self._uuid)

    def _owned_array_uuids(self) -> list[UUID]:
        """Uuids of array-instance links held by this object."""
        return array_link_uuids_of(self._uuid)
