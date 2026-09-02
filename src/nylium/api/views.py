"""Display DTOs for the nylium API.

pydantic dataclasses with extra="ignore", the morebuttons convention:
they validate on construction and serialize straight to JSON later,
when FastAPI mounts the Api class.

File-level exception to one-class-per-file: these are peer view types
of the same facade, mirroring the type/object graph they render.
"""
from __future__ import annotations

from uuid import UUID

from typing import Self, cast
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.database import Database, Instances
from nylium.objects import WObject, WProp, WType
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtypemeta import StoredValue

_CONFIG = ConfigDict(extra="ignore")


# --- type schema views ---


@dataclass(config=_CONFIG)
class PropView:
    key: str
    value_type: str


@dataclass(config=_CONFIG)
class TypeView:
    name: str
    props: list[PropView]

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def from_name(cls, name: str) -> Self:
        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        return cls(
            name=name,
            props=[
                PropView(key=prop.key, value_type=prop.value_type().name)
                for prop in WProp.all_for(owner)
            ],
        )


# --- object data views ---


@dataclass(config=_CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str


@dataclass(config=_CONFIG)
class ScalarValue:
    """None means the prop was never set."""

    value: ScalarPayload | None


@dataclass(config=_CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None


@dataclass(config=_CONFIG)
class ArrayValue:
    """None means the prop was never set; [] means set to empty."""

    items: list[PropValue] | None


PropValue = ScalarValue | RefValue | ArrayValue


@dataclass(config=_CONFIG)
class ObjectView:
    """Snapshot of one instance: every prop rendered as a typed
    ScalarValue / RefValue / ArrayValue — no Any escapes."""

    uuid: UUID
    type_name: str
    props: dict[str, PropValue]

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def from_uuid(cls, uuid: UUID) -> Self | None:
        type_uuid = Instances.type_uuid_of(uuid)
        if type_uuid is None:
            return None
        owner = WType.by_uuid(type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        wrapper = WObject.wrap(uuid)
        props = {
            prop.key: cls._render_prop(
                cast(StoredValue, getattr(wrapper, prop.key)),
                prop.value_type().name,
            )
            for prop in WProp.all_for(owner)
        }
        return cls(uuid=uuid, type_name=owner.name, props=props)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def _render_prop(cls, value: StoredValue, type_name: str) -> PropValue:
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
                items=[cls._render_prop(item, element_name) for item in value]
            )
        if value is None:
            return RefValue(ref=None)
        if not isinstance(value, WObject):
            raise TypeError(f"link prop rendered a {type(value).__name__}")
        return RefValue(
            ref=ObjectRef(uuid=value.uuid, type_name=Instances.get_type_name(value.uuid))
        )
