"""NyObject: an instance of a nylium type, backed by the tables.py graph.

Subclass it with NyScalar/NyObject/list[...] annotations; the metaclass
materializes the type and its props in the database. Attribute
reads/writes translate into queries/upserts against the *values tables:

    class Person(NyObject):
        name: NyString
        friend: "Person"
        tags: list[NyString]

    oleg = Person(name="Oleg")
    oleg.friend = maxim   # -> instance_links row, type-checked
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
from nylium.data.views.ArrayValueView import ArrayValueView
from nylium.data.views.EmbeddedValueView import EmbeddedValueView
from nylium.data.views.ObjectRefView import ObjectRefView
from nylium.data.views.RefValueView import RefValueView
from nylium.data.views.ScalarValueView import ScalarValueView
from nylium.data.views.values import PropValue
from nylium.data.views.TagView import TagView
from nylium.data.views.ObjectView import ObjectView

__all__ = [
    "ArrayValueView",
    "EmbeddedValueView",
    "ObjectRefView",
    "ObjectView",
    "PropValue",
    "RefValueView",
    "ScalarValueView",
    "TagView",
    "NyObject",
]
