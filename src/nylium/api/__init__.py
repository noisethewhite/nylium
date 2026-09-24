"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Table-domain objects, UUIDs and plain values in
and out; only the PropValue/ObjectView aggregates stay as DTOs
(ADR-0011 §5)."""
from nylium.api.Api import Api
from nylium.objects.nyobject import ObjectView
from nylium.objects.nyobject import TagView
from nylium.objects.nyobject import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
)
from nylium.objects.nyscalar import ScalarPayload

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
