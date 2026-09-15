"""Display DTOs for the nylium API (ADR-0011 §5). Package layout:

- values — the PropValue union members + ObjectRef + the shared
  dataclass config and the pinned `name` prop key
- functions — the Function<T,R> projections (ADR-0007)
- tags — the derived-tag projection (ADR-0005)
- objectview — ObjectView, the full instance snapshot renderer
"""
from nylium.api.display.functions import (
    FunctionEdgeView,
    FunctionNodeView,
    FunctionView,
)
from nylium.api.display.objectview import ObjectView
from nylium.api.display.tags import TagView
from nylium.api.display.values import (
    NAME_PROP_KEY,
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
)

__all__ = [
    "NAME_PROP_KEY",
    "ArrayValue",
    "EmbeddedValue",
    "FunctionEdgeView",
    "FunctionNodeView",
    "FunctionView",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "RefValue",
    "ScalarValue",
    "TagView",
]
