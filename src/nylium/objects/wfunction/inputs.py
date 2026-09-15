"""WFunction input materialization (ADR-0007): resolving the pinned
`input` link and projecting the input object to a plain prop-key -> value
mapping for the interpreter. A prop that is itself function-backed is
resolved recursively (composition: a function can read another
function's output)."""
from __future__ import annotations

from typing import cast
from uuid import UUID

from nylium.database import databasemethod
from nylium.tables import instances
from nylium.tables.objects.instances import get as instance_get
from nylium.tables.values.instance_values import link_for
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload
from nylium.objects.wtype import WType
from nylium.objects.wfunction.constants import INPUT_PROP_KEY
from nylium.objects.wfunction.evaluation import evaluate


@databasemethod(commit=False)
def input_object_uuid(
    function_uuid: UUID,
) -> UUID | None:
    """The object the function currently reads as its input (its pinned
    `input` link), or None when the link is unset."""
    inst = instance_get(function_uuid)
    if inst is None:
        return None
    owner = WType.by_uuid(inst.type_uuid)
    if owner is None or not owner.is_function:
        return None
    prop = WProp.by_key(owner, INPUT_PROP_KEY)
    if prop is None:
        return None
    link = link_for(function_uuid, prop.uuid)
    return None if link is None else link.uuid


@databasemethod(commit=False)
def materialize_input(function_uuid: UUID) -> dict[str, object]:
    """Project the function's input object to a prop-key -> value mapping
    the interpreter can fold over. A prop that is itself function-backed
    is resolved recursively (composition: a function can read another
    function's output). No input link -> empty mapping."""
    from nylium.objects.wobject import WObject

    input_uuid = input_object_uuid(function_uuid)
    if input_uuid is None:
        return {}
    wrapper = WObject.wrap(input_uuid)
    inst = instances.get(input_uuid)
    type_uuid = None if inst is None else inst.type_uuid
    if type_uuid is None:
        return {}
    owner = WType.by_uuid(type_uuid)
    if owner is None:
        return {}
    result: dict[str, object] = {}
    for prop in WProp.all_for(owner):
        if prop.function_uuid is not None:
            result[prop.key] = evaluate_for(prop.function_uuid)
        else:
            result[prop.key] = cast(object, getattr(wrapper, prop.key))
    return result


@databasemethod(commit=False)
def evaluate_for(function_uuid: UUID) -> ScalarPayload | None:
    """Fold the function over its current input object — the read-time
    entry point for rendering a function-backed prop."""
    return evaluate(function_uuid, materialize_input(function_uuid))
