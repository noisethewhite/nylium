"""HTTP routes: a thin namespace over the Api facade.

Handlers stay sync on purpose — the Api layer is sync SQLAlchemy, and
FastAPI runs sync endpoints in its threadpool.
"""
from __future__ import annotations

from uuid import UUID

from nylium.api.api import Api
from nylium.api.views import ObjectView, TypeView
from nylium.server.bodies import (
    CreateObjectBody,
    CreateTypeBody,
    ReorderPropsBody,
    UpdateObjectBody,
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
        return Api.create_type(body.name, body.props, body.plural_name)

    @classmethod
    def delete_type(cls, name: str) -> None:
        if not Api.delete_type(name):
            raise NotFoundError(f"no type {name!r}")

    @classmethod
    def reorder_props(cls, name: str, body: ReorderPropsBody) -> TypeView:
        return Api.reorder_props(name, body.keys)

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
