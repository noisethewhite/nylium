"""Display/CRUD facade over the object layer — the seam a future
FastAPI app mounts. Views, UUIDs and plain values in and out."""
from whiteout.api.api import Api
from whiteout.api.views import ObjectRef, ObjectView, PropView, TypeView

__all__ = ["Api", "ObjectRef", "ObjectView", "PropView", "TypeView"]
