"""WFunction input materialization (ADR-0029): projecting the owner's
sibling props to a plain prop-key -> value mapping for the interpreter.
The input is no longer a pinned object — it is the object the function is
bound into. A sibling that is itself function-backed is resolved
recursively (composition: a function can read another function's output,
chained through the owner's prop graph).

A `visiting` set breaks the self-reference / cycle at read time: if a
function's evaluation path re-enters a function already on the stack, that
edge resolves to None (empty) instead of recursing forever. Bind-time
cross-function cycle detection remains the primary guard; this is the
belt-and-suspenders stop so a slipped cycle renders empty rather than
overflowing the interpreter."""
from __future__ import annotations

from typing import cast
from uuid import UUID

from nylium.database import Database
from nylium.tables.objects.instances import instances
from nylium.tables.functions.instance_function_links import InstanceFunctionLinks
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload
from nylium.objects.wtype import WType
from nylium.objects.wfunction.evaluation import evaluate


@Database.use_same_session
def evaluate_for(inst_uuid: UUID, function_uuid: UUID) -> ScalarPayload | None:
    """Fold the function over the owner's sibling props — the read-time
    entry point for rendering a function-backed prop (ADR-0029)."""
    return _evaluate_for(inst_uuid, function_uuid, frozenset())


def _evaluate_for(
    inst_uuid: UUID, function_uuid: UUID, visiting: frozenset[UUID]
) -> ScalarPayload | None:
    if function_uuid in visiting:
        return None
    return evaluate(function_uuid, _materialize_owner(inst_uuid, visiting | {function_uuid}))


@Database.use_same_session
def materialize_owner(inst_uuid: UUID) -> dict[str, object]:
    """Project the owner object's sibling props to a prop-key -> value
    mapping. A function-backed sibling is resolved recursively."""
    return _materialize_owner(inst_uuid, frozenset())


def _materialize_owner(inst_uuid: UUID, visiting: frozenset[UUID]) -> dict[str, object]:
    wrapper = WObject.wrap(inst_uuid)
    inst = instances.get(inst_uuid)
    type_uuid = None if inst is None else inst.type_uuid
    if type_uuid is None:
        return {}
    owner = WType.by_uuid(type_uuid)
    if owner is None:
        return {}
    result: dict[str, object] = {}
    for prop in WProp.effective_for(owner):
        bound = InstanceFunctionLinks.function_uuid_for(inst_uuid, prop.uuid)
        if bound is not None:
            result[prop.key] = _evaluate_for(inst_uuid, bound, visiting)
        else:
            result[prop.key] = cast(object, getattr(wrapper, prop.key))
    return result
