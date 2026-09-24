"""NyFunction type lifecycle (ADR-0007): materializing the parameterized
Function<T, R> type with its pinned props, and the function-kind
predicate."""
from __future__ import annotations

from nylium.database import Database
from nylium.objects.NyProp import NyProp
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyString import NyString
from nylium.objects.NyType import NyType
from nylium.objects.nyfunction.constants import NAME_PROP_KEY
from nylium.server.ValidationError import ValidationError


def is_function(type_name: str) -> bool:
    owner = NyType.by_name(type_name)
    return owner is not None and owner.is_function


@Database.commit_after_this
def ensure_type(input_name: str, output_name: str) -> NyType:
    """Materialize (or fetch) the parameterized Function<T, R> type with its
    one pinned prop `name` (String). `input_name` names the owner type the
    function reads sibling props from (ADR-0029); `output_name` must name a
    scalar. The function carries no `input` link — its input is resolved at
    read time from the object it is bound into."""

    if NyScalar.by_type_name(output_name) is None:
        raise ValidationError(
            f"function output must be a scalar type, got {output_name!r}"
        )
    input_type = NyType.by_name(input_name)
    if input_type is None:
        raise ValidationError(f"no type {input_name!r} for the function input")
    if input_type.is_embedded:
        raise ValidationError(
            f"function input {input_name!r} is embedded — bind to a standalone object type"
        )
    type_name = NyType.function_name(input_name, output_name)
    owner = NyType.ensure(type_name, kind=NyType.KIND_FUNCTION)
    name_type = NyType.by_name(NyString.TYPE_NAME)
    if name_type is None:
        name_type = NyType.ensure(NyString.TYPE_NAME)
    _ = NyProp.ensure(owner, NAME_PROP_KEY, name_type, position=0)
    return owner
