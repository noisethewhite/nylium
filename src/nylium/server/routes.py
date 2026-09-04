"""HTTP routes: a thin namespace over the Api facade.

Handlers stay sync on purpose — the Api layer is sync SQLAlchemy, and
FastAPI runs sync endpoints in its threadpool.
"""
from __future__ import annotations

from uuid import UUID

from nylium.api.api import Api
from nylium.api.views import ObjectView, TypeView
from nylium.server.bodies import (
    CreateEnumBody,
    CreateObjectBody,
    CreateTypeBody,
    CreateUnitBody,
    ReorderPropsBody,
    SyncEnumOptionsBody,
    SyncPropsBody,
    SyncUnitPartsBody,
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
            body.name, body.props, body.plural_name, body.icon, body.color
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
            name, [(item.uuid, item.key, item.value_type) for item in body.props]
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
