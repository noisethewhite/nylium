"""NyFunction shared vocabulary (ADR-0007/0018): the closed node-kind set,
the pinned prop keys, the NodeType alias and the tiny type predicates
every concern module builds on."""
from __future__ import annotations

from typing import NoReturn, TypeAlias

from nylium.objects.NyType import NyType
from nylium.server.ValidationError import ValidationError
from nylium.Constants import Constants

# The closed set of node operations. The `kind` string is validated
# against this set at save time.

# The one pinned prop every function type carries: `name` (String, like
# every object type). ADR-0029 removed the `input` link prop — a function's
# input is now the sibling props of the object it is bound into.

# A node output type: an exact scalar TYPE_NAME, or an Array<ElementTypeName>.
NodeType: TypeAlias = str



def fail(message: str) -> NoReturn:

    raise ValidationError(message)


def is_numeric_scalar(name: str) -> bool:
    return name in Constants.Scalar.NUMERIC_SCALARS


def is_array_type(name: str) -> bool:
    return NyType.is_array_name(name)
