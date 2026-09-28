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

Wire DTOs live in ``nylium.data.views`` (ADR-0011); this package does
NOT re-export them — call sites import them from ``nylium.data.views``,
which breaks the ny<->views import cycle cleanly.
"""
from __future__ import annotations

from nylium.ny.nyobject.NyObject import NyObject
from nylium.ny.nyobject.AttrsMixin import AttrsMixin
from nylium.ny.nyobject.FacadeMixin import FacadeMixin
from nylium.ny.nyobject.LifecycleMixin import LifecycleMixin
from nylium.ny.nyobject.PersistenceMixin import PersistenceMixin

__all__ = [
    "AttrsMixin",
    "FacadeMixin",
    "LifecycleMixin",
    "NyObject",
    "PersistenceMixin",
]
