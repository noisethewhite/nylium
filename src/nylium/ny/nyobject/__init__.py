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

The wire DTOs live in ``nylium.data.views`` (values, tags, objectview);
this package imports them after NyObject to keep mid-package-init order.
"""
from __future__ import annotations

from nylium.ny.nyobject.NyObject import NyObject
from nylium.data.views.ArrayValue import ArrayValue
from nylium.data.views.EmbeddedValue import EmbeddedValue
from nylium.data.views.ObjectRef import ObjectRef
from nylium.data.views.RefValue import RefValue
from nylium.data.views.ScalarValue import ScalarValue
from nylium.data.views.values import PropValue
from nylium.data.views.TagView import TagView
from nylium.data.views.ObjectView import ObjectView

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
