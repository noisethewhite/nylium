"""Request bodies for the HTTP boundary.

The props payload reuses the same discriminated shape the API renders
(ScalarValue / RefValue / ArrayValue): one wire contract in both
directions, no parallel input hierarchy.

File-level exception to one-class-per-file: these are peer request
DTOs of the same boundary, mirroring the views they pair with.
"""
from __future__ import annotations

from dataclasses import field

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.api.views import PropValue

_CONFIG = ConfigDict(extra="ignore")


@dataclass(config=_CONFIG)
class CreateTypeBody:
    """props maps prop key -> value type name, like Api.create_type."""

    name: str
    props: dict[str, str] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)
