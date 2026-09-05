"""HTTP routes: a thin namespace over the Api facade.

Handlers stay sync on purpose — the Api layer is sync SQLAlchemy, and
FastAPI runs sync endpoints in its threadpool.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi.responses import FileResponse

from nylium.api.api import Api
from nylium.api.views import FunctionView, ObjectView, ScalarValue, TypeView
from nylium.server.bodies import (
    CreateEnumBody,
    CreateFunctionBody,
    CreateObjectBody,
    CreateTypeBody,
    CreateUnitBody,
    ReorderPropsBody,
    SetPropFunctionBody,
    SyncEnumOptionsBody,
    SyncPropsBody,
    SyncUnitPartsBody,
    UpdateFunctionBody,
    UpdateObjectBody,
    UpdateTypeBody,
)
from nylium.server.codec import PropCodec
from nylium.server.errors import NotFoundError


class routes:
    """Namespace-only owner for route handlers (snake_case by doctrine:
    it groups behavior, it is never instantiated)."""

    # --- types ---

    @classmethod
    def list_types(cls) -> list[TypeView]:
        return Api.list_types()

    @classmethod
    def get_type(cls, name: str) -> TypeView:
        view = Api.get_type(name)
        if view is None:
            raise NotFoundError(f"no type {name!r}")
        return view

    @classmethod
    def create_type(cls, body: CreateTypeBody) -> TypeView:
        return Api.create_type(
            body.name,
            body.props,
            body.plural_name,
            body.icon,
            body.color,
            body.embedded,
            body.formulas,
        )

    @classmethod
    def create_enum(cls, body: CreateEnumBody) -> TypeView:
        return Api.create_enum(body.name, body.options, body.icon, body.color)

    @classmethod
    def sync_enum_options(cls, name: str, body: SyncEnumOptionsBody) -> TypeView:
        return Api.sync_enum_options(
            name, [(item.uuid, item.value) for item in body.options]
        )

    @classmethod
    def create_unit(cls, body: CreateUnitBody) -> TypeView:
        return Api.create_unit(
            body.name,
            body.base,
            [(item.name, item.multiplier, item.offset) for item in body.secondaries],
            body.icon,
            body.color,
        )

    @classmethod
    def sync_unit_parts(cls, name: str, body: SyncUnitPartsBody) -> TypeView:
        return Api.sync_unit_parts(
            name,
            [
                (item.uuid, item.name, item.multiplier, item.offset, item.is_base)
                for item in body.parts
            ],
        )

    @classmethod
    def delete_type(cls, name: str) -> None:
        if not Api.delete_type(name):
            raise NotFoundError(f"no type {name!r}")

    @classmethod
    def reorder_props(cls, name: str, body: ReorderPropsBody) -> TypeView:
        return Api.reorder_props(name, body.keys)

    @classmethod
    def sync_props(cls, name: str, body: SyncPropsBody) -> TypeView:
        return Api.sync_props(
            name,
            [(item.uuid, item.key, item.value_type, item.formula) for item in body.props],
        )

    @classmethod
    def update_type(cls, name: str, body: UpdateTypeBody) -> TypeView:
        return Api.rename_type(name, body.name, body.plural_name, body.icon, body.color)

    # --- objects ---

    @classmethod
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        return Api.list_objects(type_name)

    @classmethod
    def get_object(cls, object_uuid: UUID) -> ObjectView:
        view = Api.get_object(object_uuid)
        if view is None:
            raise NotFoundError(f"no object {object_uuid}")
        return view

    @classmethod
    def create_object(cls, body: CreateObjectBody) -> ObjectView:
        decoded = PropCodec.decode(body.type_name, body.props)
        return Api.create_object(body.type_name, decoded)

    @classmethod
    def update_object(cls, object_uuid: UUID, body: UpdateObjectBody) -> ObjectView:
        view = Api.get_object(object_uuid)
        if view is None:
            raise NotFoundError(f"no object {object_uuid}")
        decoded = PropCodec.decode(view.type_name, body.props)
        return Api.update_object(object_uuid, decoded)

    @classmethod
    def delete_object(cls, object_uuid: UUID) -> None:
        if not Api.delete_object(object_uuid):
            raise NotFoundError(f"no object {object_uuid}")

    # --- files (ADR-0006) ---

    @classmethod
    def upload_file(cls, type_name: str, file: UploadFile) -> ObjectView:
        """Multipart upload; the declared MIME comes from the client and is
        validated against the target file type's policy in Api.create_file."""
        data = file.file.read()
        return Api.create_file(type_name, file.filename or "", file.content_type or "application/octet-stream", data)

    @classmethod
    def download_file(cls, file_uuid: UUID) -> FileResponse:
        view = Api.get_file(file_uuid)
        if view is None:
            raise NotFoundError(f"no file {file_uuid}")
        from nylium.objects.wfile import WFile

        path = WFile.blob_path(file_uuid)
        if not path.is_file():
            raise NotFoundError(f"blob for file {file_uuid} is missing")
        obj = Api.get_object(file_uuid)
        filename: str | None = None
        if obj is not None:
            name_prop = obj.props.get("name")
            if isinstance(name_prop, ScalarValue) and isinstance(
                name_prop.value, str
            ):
                filename = name_prop.value
        return FileResponse(path, media_type=view.mime, filename=filename)

    # --- functions (ADR-0007) ---

    @classmethod
    def list_functions(cls) -> list[FunctionView]:
        return Api.list_functions()

    @classmethod
    def get_function(cls, function_uuid: UUID) -> FunctionView:
        view = Api.get_function(function_uuid)
        if view is None:
            raise NotFoundError(f"no function {function_uuid}")
        return view

    @classmethod
    def create_function(cls, body: CreateFunctionBody) -> FunctionView:
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

    @classmethod
    def update_function(cls, function_uuid: UUID, body: UpdateFunctionBody) -> FunctionView:
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

    @classmethod
    def delete_function(cls, function_uuid: UUID) -> None:
        if not Api.delete_function(function_uuid):
            raise NotFoundError(f"no function {function_uuid}")

    @classmethod
    def set_prop_function(
        cls, name: str, prop_key: str, body: SetPropFunctionBody
    ) -> TypeView:
        return Api.set_prop_function(name, prop_key, body.function_uuid)

