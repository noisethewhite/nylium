"""Request dataclasses of the HTTP boundary and their route handlers
(ADR-0017), one domain module per file (ADR-0018).

Every route takes a request dataclass and returns a response dataclass:

- POST/PUT/PATCH routes take a JSON body — the body dataclass itself,
  with the handler as its ``route`` classmethod.
- GET/DELETE routes take path/query parameters — a small request
  dataclass bound by FastAPI through ``Depends()``; the handler is its
  classmethod (``route_get``/``route_delete``/…).
- Transport-level exceptions (binary download/export, multipart
  upload) return ``Response``/``FileResponse`` or take an extra
  ``UploadFile`` parameter — see ADR-0017.

The props payload reuses the same discriminated shape the API renders
(ScalarValue / RefValue / ArrayValue): one wire contract in both
directions, no parallel input hierarchy.

The package surface re-exports every body class, so call sites keep
addressing them as ``bodies.<Name>`` regardless of the domain module.
"""
from nylium.server.bodies.files import (
    FileUuidRequest,
    ListFilesRequest,
    RenameFileBody,
    StorageRequest,
    UploadFileRequest,
)
from nylium.server.bodies.functions import (
    CreateFunctionBody,
    FunctionEdgeInput,
    FunctionNodeInput,
    FunctionUuidRequest,
    ListFunctionsRequest,
    SetInstancePropFunctionBody,
    UpdateFunctionBody,
)
from nylium.server.bodies.formulas import (
    FormulaParseBody,
    FormulaRenderBody,
)
from nylium.server.bodies.objects import (
    CreateObjectBody,
    ListObjectsRequest,
    ObjectUuidRequest,
    UpdateObjectBody,
)
from nylium.server.bodies.traits import (
    CreateTraitBody,
    DetachTraitRequest,
    ListTraitsRequest,
    SyncTraitBody,
    SyncTraitPropItem,
    TraitAttachBody,
    TraitNameRequest,
)
from nylium.server.bodies.types import (
    CreateEnumBody,
    CreateTypeBody,
    CreateUnitBody,
    ListTypesRequest,
    ReorderPropsBody,
    SyncEnumOptionItem,
    SyncEnumOptionsBody,
    SyncPropItem,
    SyncPropsBody,
    SyncUnitPartItem,
    SyncUnitPartsBody,
    TypeNameRequest,
    UnitSecondaryInput,
    UpdateTypeBody,
)

__all__ = [
    "CreateEnumBody",
    "CreateFunctionBody",
    "CreateObjectBody",
    "CreateTraitBody",
    "CreateTypeBody",
    "CreateUnitBody",
    "DetachTraitRequest",
    "FileUuidRequest",
    "FormulaParseBody",
    "FormulaRenderBody",
    "FunctionEdgeInput",
    "FunctionNodeInput",
    "FunctionUuidRequest",
    "ListFilesRequest",
    "ListFunctionsRequest",
    "ListObjectsRequest",
    "ListTraitsRequest",
    "ListTypesRequest",
    "ObjectUuidRequest",
    "RenameFileBody",
    "ReorderPropsBody",
    "SetInstancePropFunctionBody",
    "StorageRequest",
    "SyncEnumOptionItem",
    "SyncEnumOptionsBody",
    "SyncPropItem",
    "SyncPropsBody",
    "SyncTraitBody",
    "SyncTraitPropItem",
    "SyncUnitPartItem",
    "SyncUnitPartsBody",
    "TraitAttachBody",
    "TraitNameRequest",
    "TypeNameRequest",
    "UnitSecondaryInput",
    "UpdateFunctionBody",
    "UpdateObjectBody",
    "UpdateTypeBody",
    "UploadFileRequest",
]
