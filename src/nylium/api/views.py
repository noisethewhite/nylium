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

from nylium.database import Database, EnumOptions, Instances
from nylium.objects import WObject, WProp, WType
from nylium.objects.monthday import MonthDay, MonthDayTime
from nylium.objects.wenum import WEnum
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtypemeta import StoredValue

_CONFIG = ConfigDict(extra="ignore")


# --- type schema views ---


@dataclass(config=_CONFIG)
class EnumOptionView:
    uuid: UUID
    value: str


@dataclass(config=_CONFIG)
class PropView:
    uuid: UUID
    key: str
    value_type: str


@dataclass(config=_CONFIG)
class TypeView:
    name: str
    plural_name: str | None
    icon: str
    color: str
    kind: str
    enum_options: list[EnumOptionView]
    props: list[PropView]

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def from_name(cls, name: str) -> Self:
        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        return cls(
            name=name,
            plural_name=owner.plural_name,
            icon=owner.icon,
            color=owner.color,
            kind=owner.kind,
            enum_options=[
                EnumOptionView(uuid=option.uuid, value=option.value)
                for option in EnumOptions.list_for(owner.uuid)
            ],
            props=[
                PropView(uuid=prop.uuid, key=prop.key, value_type=prop.value_type().name)
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
            # year-less calendar values cross the wire as their stamps
            if isinstance(value, (MonthDay, MonthDayTime)):
                return ScalarValue(value=str(value))
            return ScalarValue(value=cast(ScalarPayload | None, value))
        if WEnum.is_enum(type_name):
            return ScalarValue(value=cast(str | None, value))
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
