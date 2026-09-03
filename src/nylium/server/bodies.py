"""Request bodies for the HTTP boundary.

The props payload reuses the same discriminated shape the API renders
(ScalarValue / RefValue / ArrayValue): one wire contract in both
directions, no parallel input hierarchy.

File-level exception to one-class-per-file: these are peer request
DTOs of the same boundary, mirroring the views they pair with.
"""
from __future__ import annotations

from dataclasses import field
from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.api.views import PropValue

_CONFIG = ConfigDict(extra="ignore")


@dataclass(config=_CONFIG)
class CreateTypeBody:
    """props maps prop key -> value type name, like Api.create_type."""

    name: str
    plural_name: str
    props: dict[str, str] = field(default_factory=dict)
    icon: str = "inventory_2"
    color: str = "gray"


@dataclass(config=_CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class ReorderPropsBody:
    """New ordering for a type's props, as a full list of prop keys."""

    keys: list[str]


@dataclass(config=_CONFIG)
class SyncPropItem:
    """One row of the type editor's draft: uuid None = new prop."""

    key: str
    value_type: str
    uuid: UUID | None = None


@dataclass(config=_CONFIG)
class SyncPropsBody:
    """The full prop draft — renames/retypes by uuid, creates without,
    deletes whatever the draft omits."""

    props: list[SyncPropItem]


@dataclass(config=_CONFIG)
class CreateEnumBody:
    """A string enum type: name plus its allowed option values."""

    name: str
    options: list[str] = field(default_factory=list)
    icon: str = "lists"
    color: str = "gray"


@dataclass(config=_CONFIG)
class SyncEnumOptionItem:
    """One row of the enum editor's draft: uuid None = new option."""

    value: str
    uuid: UUID | None = None


@dataclass(config=_CONFIG)
class SyncEnumOptionsBody:
    """The full option draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use."""

    options: list[SyncEnumOptionItem]


@dataclass(config=_CONFIG)
class UpdateTypeBody:
    """PATCH semantics: only the listed fields change."""

    name: str | None = None
    plural_name: str | None = None
    icon: str | None = None
    color: str | None = None
