"""Typed UUID identifiers, one class per domain table.

Each class subclasses :class:`uuid.UUID` and carries a ``get()`` that
resolves the row its table owns (``Row | None`` — never raises). Scalar
value tables (``boolean_values``, ``string_values``, …) and array/element
boxes are NOT represented here: they hold no uuid of their own, so they
stay plain ``UUID`` references into ``instances``.
"""
from nylium.uuid.simple_refs import (
    CredentialRef,
    EnumOptionRef,
    FileRef,
    FunctionEdgeRef,
    FunctionRef,
    TokenRef,
    TraitDecorRef,
    TypeDecorRef,
    UnitPartRef
)

from nylium.uuid.ObjectRef import ObjectRef
from nylium.uuid.PropRef import PropRef
from nylium.uuid.TraitRef import TraitRef
from nylium.uuid.TypeRef import TypeRef
from nylium.uuid.simple_refs import UserRef
from nylium.abc import NyRef

__all__ = [
    "CredentialRef",
    "EnumOptionRef",
    "FileRef",
    "FunctionEdgeRef",
    "FunctionRef",
    "NyRef",
    "ObjectRef",
    "PropRef",
    "TokenRef",
    "TraitDecorRef",
    "TraitRef",
    "TypeDecorRef",
    "TypeRef",
    "UnitPartRef",
    "UserRef",
]
