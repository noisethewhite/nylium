"""NyObject: an instance of a nylium type, backed by the tables.py graph.

Subclass it with NyScalar/NyObject/list[...] annotations; the metaclass
materializes the type and its props in the database. Attribute
reads/writes translate into queries/upserts against the *values tables:

    class Person(NyObject):
        name: NyString
        friend: "Person"
        tags: list[NyString]

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
Import order matters: NyObject and the values/tag DTOs bind before
objectview, which imports them mid-package-init.
"""
from __future__ import annotations

from nylium.objects.nyobject.NyObject import NyObject
from nylium.objects.nyobject.ArrayValue import ArrayValue
from nylium.objects.nyobject.EmbeddedValue import EmbeddedValue
from nylium.objects.nyobject.ObjectRef import ObjectRef
from nylium.objects.nyobject.RefValue import RefValue
from nylium.objects.nyobject.ScalarValue import ScalarValue
from nylium.objects.nyobject.values import PropValue
from nylium.objects.nyobject.TagView import TagView
from nylium.objects.nyobject.ObjectView import ObjectView

__all__ = [
    "ArrayValue",
    "EmbeddedValue",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "RefValue",
    "ScalarValue",
    "TagView",
    "NyObject",
]
