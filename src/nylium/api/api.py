"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning table-domain objects (ADR-0011) and the aggregate
views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a domain object, a UUID, or a plain python value. Writes go through
the WObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/TABLE_Instances/
TABLE_Props helpers); this file only orchestrates and adapts caller input.

ADR-0015: the facade is a thin aggregator — every domain lives in its own
mixin module (one class per file), all sharing ApiShared invariants. The
public surface on `Api` is unchanged; callers keep using `Api.<method>`.
"""
from __future__ import annotations

from nylium.api.enums import EnumsApi
from nylium.api.files import FilesApi
from nylium.api.functions import FunctionsApi
from nylium.api.objects import ObjectsApi
from nylium.api.schema import SchemaApi
from nylium.api.shared import NAME_PROP_KEY as NAME_PROP_KEY
from nylium.api.shared import PropInput as PropInput
from nylium.api.traits import TraitsApi
from nylium.api.types import TypesApi
from nylium.api.units import UnitsApi


class Api(
    TypesApi,
    EnumsApi,
    UnitsApi,
    SchemaApi,
    TraitsApi,
    FilesApi,
    FunctionsApi,
    ObjectsApi,
):
    pass
