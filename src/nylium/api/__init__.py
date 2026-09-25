"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Table-domain objects, UUIDs and plain values in
and out; only the PropValue/ObjectView aggregates stay as DTOs
(ADR-0011 §5)."""
from nylium.api.Api import Api
from nylium.ny.nyobject import ObjectView
from nylium.ny.nyobject import TagView
from nylium.ny.nyobject import (
    ArrayValueView,
    EmbeddedValueView,
    ObjectRefView,
    PropValue,
    RefValueView,
    ScalarValueView,
)
from nylium.ny.NyScalar import ScalarPayload

__all__ = [
    "Api",
    "ArrayValueView",
    "EmbeddedValueView",
    "ObjectRefView",
    "ObjectView",
    "PropValue",
    "RefValueView",
    "ScalarPayload",
    "ScalarValueView",
    "TagView",
]
