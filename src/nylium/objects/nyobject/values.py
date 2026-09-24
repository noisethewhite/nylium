"""The PropValue union members (ADR-0011 §5): how one prop crosses the
wire — scalar, link ref, array or inline composition child — plus
ObjectRef, the shared pydantic config and the pinned `name` prop key."""
from __future__ import annotations

from nylium.objects.nyobject.ArrayValue import ArrayValue
from nylium.objects.nyobject.EmbeddedValue import EmbeddedValue
from nylium.objects.nyobject.RefValue import RefValue
from nylium.objects.nyobject.ScalarValue import ScalarValue
from pydantic.dataclasses import rebuild_dataclass

PropValue = ScalarValue | RefValue | ArrayValue | EmbeddedValue

# The union members reference PropValue in their annotations but can only
# import it under TYPE_CHECKING (the alias lives here, runtime import would
# cycle). Their schemas are therefore incomplete at decoration time; complete
# them now that the alias exists.
_NS = {"PropValue": PropValue}
# decorator-made dataclass, pyright can't see it -> reportArgumentType;
# return value irrelevant -> reportUnusedCallResult
_ = rebuild_dataclass(ArrayValue, force=True, _types_namespace=_NS)  # pyright: ignore[reportArgumentType]
_ = rebuild_dataclass(EmbeddedValue, force=True, _types_namespace=_NS)  # pyright: ignore[reportArgumentType]
