"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Views, UUIDs and plain values in and out."""
from nylium.api.api import Api
from nylium.api.views import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    ObjectView,
    PropValue,
    PropView,
    RefValue,
    ScalarValue,
    TagView,
    TypeView,
)
from nylium.objects.wscalar import ScalarPayload

__all__ = [
    "Api",
    "ArrayValue",
    "EmbeddedValue",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "PropView",
    "RefValue",
    "ScalarPayload",
    "ScalarValue",
    "TagView",
    "TypeView",
]
