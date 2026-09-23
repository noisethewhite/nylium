"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Table-domain objects, UUIDs and plain values in
and out; only the PropValue/ObjectView aggregates stay as DTOs
(ADR-0011 §5)."""
from nylium.api.api import Api
from nylium.objects.wobject import ObjectView
from nylium.objects.wobject import TagView
from nylium.objects.wobject import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
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
