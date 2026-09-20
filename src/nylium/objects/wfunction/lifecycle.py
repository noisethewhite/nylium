"""WFunction type lifecycle (ADR-0007): materializing the parameterized
Function<T, R> type with its pinned props, and the function-kind
predicate."""
from __future__ import annotations

from nylium.database import commit_after_this
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wfunction.constants import NAME_PROP_KEY


def is_function(type_name: str) -> bool:
    owner = WType.by_name(type_name)
    return owner is not None and owner.is_function


@commit_after_this
def ensure_type(input_name: str, output_name: str) -> WType:
    """Materialize (or fetch) the parameterized Function<T, R> type with its
    one pinned prop `name` (String). `input_name` names the owner type the
    function reads sibling props from (ADR-0029); `output_name` must name a
    scalar. The function carries no `input` link — its input is resolved at
    read time from the object it is bound into."""
    from nylium.server.errors import ValidationError

    if WScalar.by_type_name(output_name) is None:
        raise ValidationError(
            f"function output must be a scalar type, got {output_name!r}"
        )
    input_type = WType.by_name(input_name)
    if input_type is None:
        raise ValidationError(f"no type {input_name!r} for the function input")
    if input_type.is_embedded:
        raise ValidationError(
            f"function input {input_name!r} is embedded — bind to a standalone object type"
        )
    type_name = WType.function_name(input_name, output_name)
    owner = WType.ensure(type_name, kind=WType.KIND_FUNCTION)
    name_type = WType.by_name(WString.TYPE_NAME)
    if name_type is None:
        name_type = WType.ensure(WString.TYPE_NAME)
    _ = WProp.ensure(owner, NAME_PROP_KEY, name_type, position=0)
    return owner
