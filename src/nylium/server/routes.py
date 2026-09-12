"""HTTP routes: a thin namespace over the Api facade.

Handlers stay sync on purpose — the Api layer is sync SQLAlchemy, and
FastAPI runs sync endpoints in its threadpool.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi.responses import FileResponse, Response

from nylium.api.api import Api
from nylium.api.views import FunctionView, ObjectView
from nylium.server.bodies import (
    CreateEnumBody,
    CreateFunctionBody,
    CreateObjectBody,
    CreateTraitBody,
    CreateTypeBody,
    CreateUnitBody,
    RenameFileBody,
    ReorderPropsBody,
    SetPropFunctionBody,
    SyncEnumOptionsBody,
    SyncPropsBody,
    SyncTraitBody,
    SyncUnitPartsBody,
    TraitAttachBody,
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

    # Type routes serialize the domain object itself (ADR-0011 §5):
    # the wire dict carries exactly the fields the old TypeView carried.

    @classmethod
    def list_types(cls) -> list[dict[str, object]]:
        return [t.wire() for t in Api.list_types()]

    @classmethod
    def get_type(cls, name: str) -> dict[str, object]:
        view = Api.get_type(name)
        if view is None:
            raise NotFoundError(f"no type {name!r}")
        return view.wire()

    @classmethod
    def create_type(cls, body: CreateTypeBody) -> dict[str, object]:
        return Api.create_type(
            body.name,
            body.props,
            body.plural_name,
            body.icon,
            body.color,
            body.embedded,
            body.formulas,
        ).wire()

    @classmethod
    def create_enum(cls, body: CreateEnumBody) -> dict[str, object]:
        return Api.create_enum(body.name, body.options, body.icon, body.color).wire()

    @classmethod
    def sync_enum_options(cls, name: str, body: SyncEnumOptionsBody) -> dict[str, object]:
        return Api.sync_enum_options(
            name, [(item.uuid, item.value) for item in body.options]
        ).wire()

    @classmethod
    def create_unit(cls, body: CreateUnitBody) -> dict[str, object]:
        return Api.create_unit(
            body.name,
            body.base,
            [(item.name, item.multiplier, item.offset) for item in body.secondaries],
            body.icon,
            body.color,
        ).wire()

    @classmethod
    def sync_unit_parts(cls, name: str, body: SyncUnitPartsBody) -> dict[str, object]:
        return Api.sync_unit_parts(
            name,
            [
                (item.uuid, item.name, item.multiplier, item.offset, item.is_base)
                for item in body.parts
            ],
        ).wire()

    @classmethod
    def delete_type(cls, name: str) -> None:
        if not Api.delete_type(name):
            raise NotFoundError(f"no type {name!r}")

    @classmethod
    def reorder_props(cls, name: str, body: ReorderPropsBody) -> dict[str, object]:
        return Api.reorder_props(name, body.keys).wire()

    @classmethod
    def sync_props(cls, name: str, body: SyncPropsBody) -> dict[str, object]:
        return Api.sync_props(
            name,
            [(item.uuid, item.key, item.value_type, item.formula) for item in body.props],
        ).wire()

    @classmethod
    def update_type(cls, name: str, body: UpdateTypeBody) -> dict[str, object]:
        return Api.rename_type(name, body.name, body.plural_name, body.icon, body.color).wire()

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

    @classmethod
    def export_object(cls, object_uuid: UUID) -> Response:
        result = Api.export_markdown(object_uuid)
        if result is None:
            raise NotFoundError(f"no object {object_uuid}")
        filename, content = result
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # --- files (ADR-0008) ---

    @classmethod
    def storage_stats(cls) -> dict[str, int]:
        return Api.storage_stats()

    @classmethod
    def upload_file(cls, type_name: str, file: UploadFile) -> dict[str, object]:
        """Multipart upload; the declared MIME comes from the client and is
        validated against the target file type's policy in Api.create_file."""
        data = file.file.read()
        return Api.create_file(type_name, file.filename or "", file.content_type or "application/octet-stream", data).wire()

    @classmethod
    def list_files(cls) -> list[dict[str, object]]:
        return [f.wire() for f in Api.list_files()]

    @classmethod
    def get_file(cls, file_uuid: UUID) -> dict[str, object]:
        view = Api.get_file(file_uuid)
        if view is None:
            raise NotFoundError(f"no file {file_uuid}")
        return view.wire()

    @classmethod
    def rename_file(cls, file_uuid: UUID, body: RenameFileBody) -> dict[str, object]:
        view = Api.get_file(file_uuid)
        if view is None:
            raise NotFoundError(f"no file {file_uuid}")
        return Api.rename_file(file_uuid, body.name).wire()

    @classmethod
    def delete_file(cls, file_uuid: UUID) -> None:
        if not Api.delete_file(file_uuid):
            raise NotFoundError(f"no file {file_uuid}")

    @classmethod
    def download_file(cls, file_uuid: UUID) -> FileResponse:
        view = Api.get_file(file_uuid)
        if view is None:
            raise NotFoundError(f"no file {file_uuid}")
        from nylium.objects.wfile import WFile

        path = WFile.blob_path(file_uuid)
        if not path.is_file():
            raise NotFoundError(f"blob for file {file_uuid} is missing")
        # ADR-0008: name is a column on the files row, not an object prop
        return FileResponse(path, media_type=view.mime, filename=view.name)

    # --- functions (ADR-0007) ---

    # --- traits (ADR-0013) ---

    @classmethod
    def list_traits(cls) -> list[dict[str, object]]:
        return [t.wire() for t in Api.list_traits()]

    @classmethod
    def get_trait(cls, name: str) -> dict[str, object]:
        view = Api.get_trait(name)
        if view is None:
            raise NotFoundError(f"no trait {name!r}")
        return view.wire()

    @classmethod
    def create_trait(cls, body: CreateTraitBody) -> dict[str, object]:
        return Api.create_trait(body.name, body.color, body.props).wire()

    @classmethod
    def sync_trait(cls, name: str, body: SyncTraitBody) -> dict[str, object]:
        items: list[tuple[UUID | None, str, str, str | None]] | None = (
            None
            if body.props is None
            else [(item.uuid, item.key, item.value_type, None) for item in body.props]
        )
        return Api.sync_trait(name, body.name, body.color, items).wire()

    @classmethod
    def delete_trait(cls, name: str) -> None:
        if not Api.delete_trait(name):
            raise NotFoundError(f"no trait {name!r}")

    @classmethod
    def attach_trait(cls, name: str, body: TraitAttachBody) -> dict[str, object]:
        return Api.attach_trait(name, body.trait).wire()

    @classmethod
    def detach_trait(cls, name: str, trait: str) -> dict[str, object]:
        return Api.detach_trait(name, trait).wire()

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
    ) -> dict[str, object]:
        return Api.set_prop_function(name, prop_key, body.function_uuid).wire()

