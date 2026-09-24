"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning table-domain objects (ADR-0011) and the aggregate
views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
NyObject wrappers or SQLAlchemy rows to callers: everything in and out
is a domain object, a UUID, or a plain python value. Writes go through
the NyObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/Instances/
Props helpers); this file only orchestrates and adapts caller input.

ADR-0015: the facade is a thin aggregator — every domain lives in its own
mixin module (one class per file), all sharing ApiShared invariants. The
public surface on `Api` is unchanged; callers keep using `Api.<method>`.
"""
from __future__ import annotations

from nylium.api.EnumsApi import EnumsApi
from nylium.api.FilesApi import FilesApi
from nylium.api.FunctionsApi import FunctionsApi
from nylium.api.ObjectsApi import ObjectsApi
from nylium.api.SchemaApi import SchemaApi
from nylium.Constants import Constants
from nylium.api.ApiShared import PropInput as PropInput
from nylium.api.TraitsApi import TraitsApi
from nylium.api.TypesApi import TypesApi
from nylium.api.UnitsApi import UnitsApi

NAME_PROP_KEY = Constants.Props.NAME_PROP_KEY


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
