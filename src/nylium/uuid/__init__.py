"""Typed UUID identifiers, one class per domain table.

Each class subclasses :class:`uuid.UUID` and carries a ``get()`` that
resolves the row its table owns (``Row | None`` — never raises). Scalar
value tables (``boolean_values``, ``string_values``, …) and array/element
boxes are NOT represented here: they hold no uuid of their own, so they
stay plain ``UUID`` references into ``instances``.
"""
from nylium.uuid.CredentialUUID import CredentialUUID
from nylium.uuid.EnumOptionUUID import EnumOptionUUID
from nylium.uuid.FileUUID import FileUUID
from nylium.uuid.FunctionEdgeUUID import FunctionEdgeUUID
from nylium.uuid.FunctionUUID import FunctionUUID
from nylium.uuid.ObjectUUID import ObjectUUID
from nylium.uuid.PropUUID import PropUUID
from nylium.uuid.TokenUUID import TokenUUID
from nylium.uuid.TraitDecorUUID import TraitDecorUUID
from nylium.uuid.TraitUUID import TraitUUID
from nylium.uuid.TypeDecorUUID import TypeDecorUUID
from nylium.uuid.TypeUUID import TypeUUID
from nylium.uuid.UnitPartUUID import UnitPartUUID
from nylium.uuid.UserUUID import UserUUID

__all__ = [
    "CredentialUUID",
    "EnumOptionUUID",
    "FileUUID",
    "FunctionEdgeUUID",
    "FunctionUUID",
    "ObjectUUID",
    "PropUUID",
    "TokenUUID",
    "TraitDecorUUID",
    "TraitUUID",
    "TypeDecorUUID",
    "TypeUUID",
    "UnitPartUUID",
    "UserUUID",
]
