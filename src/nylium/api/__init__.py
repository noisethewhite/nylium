"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Table-domain objects, UUIDs and plain values in
and out; only the PropValue/ObjectView aggregates stay as DTOs
(ADR-0011 §5)."""
from nylium.api.api import Api
from nylium.api.views import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    ObjectView,
    PropValue,
    RefValue,
    ScalarValue,
    TagView,
)
from nylium.objects.wscalar import ScalarPayload

__all__ = [
    "Api",
    "ArrayValue",
    "EmbeddedValue",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "RefValue",
    "ScalarPayload",
    "ScalarValue",
    "TagView",
]
