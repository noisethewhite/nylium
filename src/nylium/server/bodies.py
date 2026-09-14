"""Request dataclasses of the HTTP boundary and their route handlers
(ADR-0017).

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

File-level exception to one-class-per-file: these are peer request
DTOs of the same boundary, mirroring the views they pair with.
"""
from __future__ import annotations

import sys
import typing
from collections.abc import Mapping
from dataclasses import dataclass as plain_dataclass, field
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, UploadFile, params
from fastapi.responses import FileResponse, Response
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.api.api import Api
from nylium.api.views import FunctionView, ObjectView, PropValue
from nylium.objects.wscalar import WColor
from nylium.server.codec import PropCodec
from nylium.server.errors import NotFoundError
from nylium.server.views import FileView, StorageStats, TraitView, TypeView

_CONFIG = ConfigDict(extra="ignore")

# FastAPI binds a dataclass dependency's __init__ parameters from the
# path/query by name — that is how GET/DELETE requests become typed.
_Path: params.Depends = Depends()  # pyright: ignore[reportAny]


# --- types ---


@dataclass(config=_CONFIG)
class CreateTypeBody:
    """props maps prop key -> value type name, like Api.create_type."""

    name: str
    plural_name: str
    props: dict[str, str] = field(default_factory=dict)
    # ADR-0005: optional prop key -> formula string
    formulas: dict[str, str] | None = None
    icon: str = "inventory_2"
    color: str = WColor.DEFAULT
    # ADR-0004: composition type — instances exist only as prop values
    embedded: bool = False

    @classmethod
    def route(cls, body: "CreateTypeBody") -> TypeView:
        return TypeView.from_row(
            Api.create_type(
                body.name,
                body.props,
                body.plural_name,
                body.icon,
                body.color,
                body.embedded,
                body.formulas,
            )
        )


@dataclass(config=_CONFIG)
class CreateEnumBody:
    """A string enum type: name plus its allowed option values."""

    name: str
    options: list[str] = field(default_factory=list)
    icon: str = "lists"
    color: str = WColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateEnumBody") -> TypeView:
        return TypeView.from_row(
            Api.create_enum(body.name, body.options, body.icon, body.color)
        )


@dataclass(config=_CONFIG)
class SyncEnumOptionItem:
    """One row of the enum editor's draft: uuid None = new option."""

    value: str
    uuid: UUID | None = None


@dataclass(config=_CONFIG)
class SyncEnumOptionsBody:
    """The full option draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use."""

    options: list[SyncEnumOptionItem]

    @classmethod
    def route(cls, name: str, body: "SyncEnumOptionsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_enum_options(
                name, [(item.uuid, item.value) for item in body.options]
            )
        )


@dataclass(config=_CONFIG)
class UnitSecondaryInput:
    """One secondary part of a new unit: name and the affine conversion
    factor (base = (entered - offset) / multiplier)."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)


@dataclass(config=_CONFIG)
class CreateUnitBody:
    """A unit type: name, its base part, and optional secondary parts."""

    name: str
    base: str
    secondaries: list[UnitSecondaryInput] = field(default_factory=list)
    icon: str = "straighten"
    color: str = WColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateUnitBody") -> TypeView:
        return TypeView.from_row(
            Api.create_unit(
                body.name,
                body.base,
                [
                    (item.name, item.multiplier, item.offset)
                    for item in body.secondaries
                ],
                body.icon,
                body.color,
            )
        )


@dataclass(config=_CONFIG)
class SyncUnitPartItem:
    """One row of the unit editor's draft: uuid None = new part."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)
    is_base: bool = False
    uuid: UUID | None = None


@dataclass(config=_CONFIG)
class SyncUnitPartsBody:
    """The full part draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use. Exactly one part must carry is_base."""

    parts: list[SyncUnitPartItem]

    @classmethod
    def route(cls, name: str, body: "SyncUnitPartsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_unit_parts(
                name,
                [
                    (item.uuid, item.name, item.multiplier, item.offset, item.is_base)
                    for item in body.parts
                ],
            )
        )


@dataclass(config=_CONFIG)
class ReorderPropsBody:
    """New ordering for a type's props, as a full list of prop keys."""

    keys: list[str]

    @classmethod
    def route(cls, name: str, body: "ReorderPropsBody") -> TypeView:
        return TypeView.from_row(Api.reorder_props(name, body.keys))


@dataclass(config=_CONFIG)
class SyncPropItem:
    """One row of the type editor's draft: uuid None = new prop."""

    key: str
    value_type: str
    uuid: UUID | None = None
    # ADR-0005: a formula over the owner's Array<T> props, or None
    formula: str | None = None


@dataclass(config=_CONFIG)
class SyncPropsBody:
    """The full prop draft — renames/retypes by uuid, creates without,
    deletes whatever the draft omits."""

    props: list[SyncPropItem]

    @classmethod
    def route(cls, name: str, body: "SyncPropsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_props(
                name,
                [(item.uuid, item.key, item.value_type, item.formula) for item in body.props],
            )
        )


@dataclass(config=_CONFIG)
class UpdateTypeBody:
    """PATCH semantics: only the listed fields change."""

    name: str | None = None
    plural_name: str | None = None
    icon: str | None = None
    color: str | None = None

    @classmethod
    def route(cls, name: str, body: "UpdateTypeBody") -> TypeView:
        return TypeView.from_row(
            Api.rename_type(name, body.name, body.plural_name, body.icon, body.color)
        )


@plain_dataclass
class TypeNameRequest:
    """Path-bound input of the single-type GET/DELETE routes."""

    name: str

    @classmethod
    def route_get(cls, request: Annotated["TypeNameRequest", _Path]) -> TypeView:
        type_ = Api.get_type(request.name)
        if type_ is None:
            raise NotFoundError(f"no type {request.name!r}")
        return TypeView.from_row(type_)

    @classmethod
    def route_delete(cls, request: Annotated["TypeNameRequest", _Path]) -> Response:
        if not Api.delete_type(request.name):
            raise NotFoundError(f"no type {request.name!r}")
        return Response(status_code=204)


@plain_dataclass
class ListTypesRequest:
    """No-input request of GET /types."""

    @classmethod
    def route(cls, _request: Annotated["ListTypesRequest", _Path]) -> list[TypeView]:
        return [TypeView.from_row(type_) for type_ in Api.list_types()]


# --- traits (ADR-0013) ---


@dataclass(config=_CONFIG)
class CreateTraitBody:
    """A trait (ADR-0013): name, color, and a prop bundle — the same
    key -> value spec shape as CreateTypeBody.props."""

    name: str
    props: dict[str, str] = field(default_factory=dict)
    color: str = WColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateTraitBody") -> TraitView:
        return TraitView.from_row(Api.create_trait(body.name, body.color, body.props))


@dataclass(config=_CONFIG)
class SyncTraitPropItem:
    """One row of the trait editor's draft: uuid None = new prop.
    Traits v1 have no formulas — no formula field."""

    key: str
    value_type: str
    uuid: UUID | None = None


@dataclass(config=_CONFIG)
class SyncTraitBody:
    """PUT semantics: identity + the full prop draft (renames/retypes by
    uuid, creates without, deletes whatever the draft omits)."""

    name: str | None = None
    color: str | None = None
    props: list[SyncTraitPropItem] | None = None

    @classmethod
    def route(cls, name: str, body: "SyncTraitBody") -> TraitView:
        items: list[tuple[UUID | None, str, str, str | None]] | None = (
            None
            if body.props is None
            else [(item.uuid, item.key, item.value_type, None) for item in body.props]
        )
        return TraitView.from_row(Api.sync_trait(name, body.name, body.color, items))


@plain_dataclass
class TraitNameRequest:
    """Path-bound input of the single-trait GET/DELETE routes."""

    name: str

    @classmethod
    def route_get(cls, request: Annotated["TraitNameRequest", _Path]) -> TraitView:
        trait = Api.get_trait(request.name)
        if trait is None:
            raise NotFoundError(f"no trait {request.name!r}")
        return TraitView.from_row(trait)

    @classmethod
    def route_delete(cls, request: Annotated["TraitNameRequest", _Path]) -> Response:
        if not Api.delete_trait(request.name):
            raise NotFoundError(f"no trait {request.name!r}")
        return Response(status_code=204)


@plain_dataclass
class ListTraitsRequest:
    """No-input request of GET /traits."""

    @classmethod
    def route(cls, _request: Annotated["ListTraitsRequest", _Path]) -> list[TraitView]:
        return [TraitView.from_row(trait) for trait in Api.list_traits()]


@dataclass(config=_CONFIG)
class TraitAttachBody:
    """Attach/detach a trait to/from a type."""

    trait: str

    @classmethod
    def route(cls, name: str, body: "TraitAttachBody") -> TypeView:
        return TypeView.from_row(Api.attach_trait(name, body.trait))


@plain_dataclass
class DetachTraitRequest:
    """Path-bound input of DELETE /types/{name}/traits/{trait}."""

    name: str
    trait: str

    @classmethod
    def route(cls, request: Annotated["DetachTraitRequest", _Path]) -> TypeView:
        return TypeView.from_row(Api.detach_trait(request.name, request.trait))


# --- objects ---


@dataclass(config=_CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, body: "CreateObjectBody") -> ObjectView:
        decoded = PropCodec.decode(body.type_name, body.props)
        return Api.create_object(body.type_name, decoded)


@dataclass(config=_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, object_uuid: UUID, body: "UpdateObjectBody") -> ObjectView:
        view = Api.get_object(object_uuid)
        if view is None:
            raise NotFoundError(f"no object {object_uuid}")
        decoded = PropCodec.decode(view.type_name, body.props)
        return Api.update_object(object_uuid, decoded)


@plain_dataclass
class ListObjectsRequest:
    """Query-bound input of GET /objects (type_name filter)."""

    type_name: str

    @classmethod
    def route(cls, request: Annotated["ListObjectsRequest", _Path]) -> list[ObjectView]:
        return Api.list_objects(request.type_name)


@plain_dataclass
class ObjectUuidRequest:
    """Path-bound input of the single-object routes."""

    object_uuid: UUID

    @classmethod
    def route_get(cls, request: Annotated["ObjectUuidRequest", _Path]) -> ObjectView:
        view = Api.get_object(request.object_uuid)
        if view is None:
            raise NotFoundError(f"no object {request.object_uuid}")
        return view

    @classmethod
    def route_delete(cls, request: Annotated["ObjectUuidRequest", _Path]) -> Response:
        if not Api.delete_object(request.object_uuid):
            raise NotFoundError(f"no object {request.object_uuid}")
        return Response(status_code=204)

    @classmethod
    def route_export(cls, request: Annotated["ObjectUuidRequest", _Path]) -> Response:
        result = Api.export_markdown(request.object_uuid)
        if result is None:
            raise NotFoundError(f"no object {request.object_uuid}")
        filename, content = result
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# --- files (ADR-0008) ---


@dataclass(config=_CONFIG)
class RenameFileBody:
    """ADR-0008: rename a file entity's display name. The uuid pointer is
    stable, so references never break."""

    name: str

    @classmethod
    def route(cls, file_uuid: UUID, body: "RenameFileBody") -> FileView:
        if Api.get_file(file_uuid) is None:
            raise NotFoundError(f"no file {file_uuid}")
        return FileView.from_row(Api.rename_file(file_uuid, body.name))


@plain_dataclass
class UploadFileRequest:
    """Query-bound input of the multipart upload route. The UploadFile
    itself is a transport-level parameter next to the dataclass."""

    type_name: str

    @classmethod
    def route(
        cls, request: Annotated["UploadFileRequest", _Path], file: UploadFile
    ) -> FileView:
        """Multipart upload; the declared MIME comes from the client and is
        validated against the target file type's policy in Api.create_file."""
        data = file.file.read()
        return FileView.from_row(
            Api.create_file(
                request.type_name,
                file.filename or "",
                file.content_type or "application/octet-stream",
                data,
            )
        )


@plain_dataclass
class ListFilesRequest:
    """No-input request of GET /files."""

    @classmethod
    def route(cls, _request: Annotated["ListFilesRequest", _Path]) -> list[FileView]:
        return [FileView.from_row(file) for file in Api.list_files()]


@plain_dataclass
class FileUuidRequest:
    """Path-bound input of the single-file routes."""

    file_uuid: UUID

    @classmethod
    def route_get(cls, request: Annotated["FileUuidRequest", _Path]) -> FileView:
        file = Api.get_file(request.file_uuid)
        if file is None:
            raise NotFoundError(f"no file {request.file_uuid}")
        return FileView.from_row(file)

    @classmethod
    def route_delete(cls, request: Annotated["FileUuidRequest", _Path]) -> Response:
        if not Api.delete_file(request.file_uuid):
            raise NotFoundError(f"no file {request.file_uuid}")
        return Response(status_code=204)

    @classmethod
    def route_download(cls, request: Annotated["FileUuidRequest", _Path]) -> FileResponse:
        from nylium.objects.wfile import WFile

        file = Api.get_file(request.file_uuid)
        if file is None:
            raise NotFoundError(f"no file {request.file_uuid}")
        path = WFile.blob_path(request.file_uuid)
        if not path.is_file():
            raise NotFoundError(f"blob for file {request.file_uuid} is missing")
        return FileResponse(path, media_type=file.mime, filename=file.name)


@plain_dataclass
class StorageRequest:
    """No-input request of GET /storage."""

    @classmethod
    def route(cls, _request: Annotated["StorageRequest", _Path]) -> StorageStats:
        stats = Api.storage_stats()
        return StorageStats(
            total_bytes=stats["total_bytes"],
            used_bytes=stats["used_bytes"],
            free_bytes=stats["free_bytes"],
            nylium_bytes=stats["nylium_bytes"],
        )


# --- functions (ADR-0007) ---


@dataclass(config=_CONFIG)
class FunctionNodeInput:
    """One node of a function's action DAG draft (ADR-0007). The client
    generates the uuid so edges can reference not-yet-created nodes."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class FunctionEdgeInput:
    """A dataflow edge between two node uuids in a DAG draft."""

    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int


@dataclass(config=_CONFIG)
class CreateFunctionBody:
    """A Function<T,R> instance: parameterization, input link and the
    full action DAG in one draft."""

    input_type: str
    output_type: str
    name: str
    input_object_uuid: UUID | None = None
    nodes: list[FunctionNodeInput] = field(default_factory=list)
    edges: list[FunctionEdgeInput] = field(default_factory=list)

    @classmethod
    def route(cls, body: "CreateFunctionBody") -> FunctionView:
        return Api.create_function(
            body.input_type,
            body.output_type,
            body.name,
            body.input_object_uuid,
            [(n.uuid, n.kind, n.position, n.config) for n in body.nodes],
            [
                (e.from_node_uuid, e.from_port, e.to_node_uuid, e.to_port)
                for e in body.edges
            ],
        )


@dataclass(config=_CONFIG)
class UpdateFunctionBody:
    """Replace a function's name, input link and DAG (full-draft PUT
    semantics — the input/output parameterization is fixed)."""

    name: str
    input_object_uuid: UUID | None = None
    nodes: list[FunctionNodeInput] = field(default_factory=list)
    edges: list[FunctionEdgeInput] = field(default_factory=list)

    @classmethod
    def route(cls, function_uuid: UUID, body: "UpdateFunctionBody") -> FunctionView:
        return Api.update_function(
            function_uuid,
            body.name,
            body.input_object_uuid,
            [(n.uuid, n.kind, n.position, n.config) for n in body.nodes],
            [
                (e.from_node_uuid, e.from_port, e.to_node_uuid, e.to_port)
                for e in body.edges
            ],
        )


@plain_dataclass
class ListFunctionsRequest:
    """No-input request of GET /functions."""

    @classmethod
    def route(cls, _request: Annotated["ListFunctionsRequest", _Path]) -> list[FunctionView]:
        return Api.list_functions()


@plain_dataclass
class FunctionUuidRequest:
    """Path-bound input of the single-function routes."""

    function_uuid: UUID

    @classmethod
    def route_get(cls, request: Annotated["FunctionUuidRequest", _Path]) -> FunctionView:
        view = Api.get_function(request.function_uuid)
        if view is None:
            raise NotFoundError(f"no function {request.function_uuid}")
        return view

    @classmethod
    def route_delete(cls, request: Annotated["FunctionUuidRequest", _Path]) -> Response:
        if not Api.delete_function(request.function_uuid):
            raise NotFoundError(f"no function {request.function_uuid}")
        return Response(status_code=204)


@dataclass(config=_CONFIG)
class SetPropFunctionBody:
    """Bind a Function<T,R> instance to a prop (None unbinds)."""

    function_uuid: UUID | None = None

    @classmethod
    def route(cls, name: str, prop_key: str, body: "SetPropFunctionBody") -> TypeView:
        return TypeView.from_row(
            Api.set_prop_function(name, prop_key, body.function_uuid)
        )


def _resolve_route_hints() -> None:
    """Evaluate forward references in the route signatures.

    A handler annotates its own class by name, which is not yet bound
    while the class body executes; resolve those annotations to the real
    classes now, before FastAPI inspects the signatures (it uses the
    dependency annotation as the Depends() target class verbatim)."""
    module = sys.modules[__name__]
    members = typing.cast("Mapping[str, object]", vars(module))
    for value in members.values():
        if not isinstance(value, type) or value.__module__ != __name__:
            continue
        attrs = typing.cast("Mapping[str, object]", vars(value))
        for attr in attrs.values():
            fn = typing.cast("object", getattr(attr, "__func__", attr))
            name = typing.cast("object", getattr(fn, "__name__", ""))
            if not callable(fn) or not isinstance(name, str):
                continue
            if not name.startswith("route"):
                continue
            fn.__annotations__ = typing.get_type_hints(
                fn, vars(module), include_extras=True
            )


_resolve_route_hints()
