"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Table-domain objects, UUIDs and plain values in
and out; only the PropValue/ObjectView aggregates stay as DTOs
(ADR-0011 §5)."""
from nylium.api.Api import Api
from nylium.data.views import ObjectView
from nylium.data.views import TagView
from nylium.data.views import (
    ArrayValueView,
    EmbeddedValueView,
    ObjectRefView,
    PropValue,
    RefValueView,
    ScalarValueView,
)
from nylium.ny.NyScalar import ScalarPayload
from nylium.api.ApiShared import ApiShared, PropInput
from nylium.api.EnumsApi import EnumsApi
from nylium.api.FilesApi import FilesApi
from nylium.api.FunctionsApi import FunctionsApi
from nylium.api.MarkdownRenderer import MarkdownRenderer
from nylium.api.ObjectsApi import ObjectsApi
from nylium.api.SchemaApi import SchemaApi
from nylium.api.TraitsApi import TraitsApi
from nylium.api.TypesApi import TypesApi
from nylium.api.UnitsApi import UnitsApi

__all__ = [
    "Api",
    "ApiShared",
    "ArrayValueView",
    "EmbeddedValueView",
    "EnumsApi",
    "FilesApi",
    "FunctionsApi",
    "MarkdownRenderer",
    "ObjectRefView",
    "ObjectView",
    "ObjectsApi",
    "PropInput",
    "PropValue",
    "RefValueView",
    "ScalarPayload",
    "ScalarValueView",
    "SchemaApi",
    "TagView",
    "TraitsApi",
    "TypesApi",
    "UnitsApi",
]
