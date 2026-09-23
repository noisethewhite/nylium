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

The class is composed from single-concern mixins (ADR-0018):
lifecycle (construction/retrieval/delete), facade (UI rendering,
dunders), attrs (__getattr__/__setattr__ dispatch) over persistence
(raw *values-table reads/writes).

The wire DTOs live here too: values (the PropValue union + ObjectRef),
tags (the ADR-0005 projection), objectview (the full snapshot).
Import order matters: WObject and the values/tag DTOs bind before
objectview, which imports them mid-package-init.
"""
from __future__ import annotations

from nylium.objects.wobject.constants import (
    INSTANCE_NAME_FORMAT,
    PRIVATE_PREFIX,
    SHORT_UUID_LENGTH,
)
from nylium.objects.wobject.object import WObject
from nylium.objects.wobject.values import (
    CONFIG,
    NAME_PROP_KEY,
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
)
from nylium.objects.wobject.tags import TagView
from nylium.objects.wobject.objectview import ObjectView

__all__ = [
    "CONFIG",
    "INSTANCE_NAME_FORMAT",
    "NAME_PROP_KEY",
    "PRIVATE_PREFIX",
    "SHORT_UUID_LENGTH",
    "ArrayValue",
    "EmbeddedValue",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "RefValue",
    "ScalarValue",
    "TagView",
    "WObject",
]
