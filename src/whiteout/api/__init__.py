"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Views, UUIDs and plain values in and out."""
from whiteout.api.api import Api
from whiteout.api.views import (
    ArrayValue,
    ObjectRef,
    ObjectView,
    PropValue,
    PropView,
    RefValue,
    ScalarValue,
    TypeView,
)
from whiteout.objects.wscalar import ScalarPayload

__all__ = [
    "Api",
    "ArrayValue",
    "ObjectRef",
    "ObjectView",
    "PropValue",
    "PropView",
    "RefValue",
    "ScalarPayload",
    "ScalarValue",
    "TypeView",
]
