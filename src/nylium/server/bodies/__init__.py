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
(ScalarValueView / RefValueView / ArrayValueView): one wire contract in both
directions, no parallel input hierarchy.

The package surface re-exports every body class, so call sites keep
addressing them as ``bodies.<Name>`` regardless of the domain module.
"""
from nylium.server.bodies.FileUuidRequest import FileUuidRequest
from nylium.server.bodies.ListFilesRequest import ListFilesRequest
from nylium.server.bodies.RenameFileBody import RenameFileBody
from nylium.server.bodies.StorageRequest import StorageRequest
from nylium.server.bodies.UploadFileRequest import UploadFileRequest
from nylium.server.bodies.CreateFunctionBody import CreateFunctionBody
from nylium.server.bodies.FunctionEdgeInput import FunctionEdgeInput
from nylium.server.bodies.FunctionNodeInput import FunctionNodeInput
from nylium.server.bodies.FunctionUuidRequest import FunctionUuidRequest
from nylium.server.bodies.ListFunctionsRequest import ListFunctionsRequest
from nylium.server.bodies.SetInstancePropFunctionBody import SetInstancePropFunctionBody
from nylium.server.bodies.UpdateFunctionBody import UpdateFunctionBody
from nylium.server.bodies.FormulaParseBody import FormulaParseBody
from nylium.server.bodies.FormulaRenderBody import FormulaRenderBody
from nylium.server.bodies.CreateObjectBody import CreateObjectBody
from nylium.server.bodies.ListObjectsRequest import ListObjectsRequest
from nylium.server.bodies.ObjectUuidRequest import ObjectUuidRequest
from nylium.server.bodies.UpdateObjectBody import UpdateObjectBody
from nylium.server.bodies.CreateTraitBody import CreateTraitBody
from nylium.server.bodies.DetachTraitRequest import DetachTraitRequest
from nylium.server.bodies.ListTraitsRequest import ListTraitsRequest
from nylium.server.bodies.SyncTraitBody import SyncTraitBody
from nylium.server.bodies.SyncTraitPropItem import SyncTraitPropItem
from nylium.server.bodies.TraitAttachBody import TraitAttachBody
from nylium.server.bodies.TraitNameRequest import TraitNameRequest
from nylium.server.bodies.CreateEnumBody import CreateEnumBody
from nylium.server.bodies.CreateTypeBody import CreateTypeBody
from nylium.server.bodies.CreateUnitBody import CreateUnitBody
from nylium.server.bodies.ListTypesRequest import ListTypesRequest
from nylium.server.bodies.ReorderPropsBody import ReorderPropsBody
from nylium.server.bodies.SyncEnumOptionItem import SyncEnumOptionItem
from nylium.server.bodies.SyncEnumOptionsBody import SyncEnumOptionsBody
from nylium.server.bodies.SyncPropItem import SyncPropItem
from nylium.server.bodies.SyncPropsBody import SyncPropsBody
from nylium.server.bodies.SyncUnitPartItem import SyncUnitPartItem
from nylium.server.bodies.SyncUnitPartsBody import SyncUnitPartsBody
from nylium.server.bodies.TypeNameRequest import TypeNameRequest
from nylium.server.bodies.UnitSecondaryInput import UnitSecondaryInput
from nylium.server.bodies.UpdateTypeBody import UpdateTypeBody

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
