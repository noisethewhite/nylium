"""Object CRUD and markdown export (ADR-0015)."""
from __future__ import annotations

from collections.abc import Callable
from typing import cast
from uuid import UUID

from nylium.api.shared import ApiShared, NAME_PROP_KEY, PropInput
from nylium.api.display import ObjectRef, ObjectView
from nylium.database import Database
from nylium.objects.navigation import type_name_of
from nylium.tables.objects.instances import instances
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import WTypeMeta


class ObjectsApi(ApiShared):
    @classmethod
    @Database.use_same_session
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        owner = WType.by_name(type_name)
        if owner is None:
            return []
        if owner.is_embedded:
            # composition children never list standalone (ADR-0004) —
            # this also keeps them out of every ref picker
            return []
        views = [
            ObjectView.from_uuid(uuid)
            for uuid in [i.uuid for i in instances.where(type_uuid=owner.uuid)]
        ]
        return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        return ObjectView.from_uuid(uuid)

    @classmethod
    @Database.use_same_session
    def export_markdown(cls, uuid: UUID) -> tuple[str, str] | None:
        """Render an object as a markdown document for download.

        Links to other objects render as `[label](object:<uuid>)` — the
        display name up front, the pointer kept in the href. Nothing is
        expanded recursively (a graph is not a tree). Returns
        (filename, content) or None when the object does not exist.
        """
        from nylium.api.markdown import MarkdownRenderer

        view = ObjectView.from_uuid(uuid)
        if view is None:
            return None

        def ref_label(ref: ObjectRef) -> str:
            inst = instances.get(ref.uuid)
            owner = WType.by_uuid(inst.type_uuid) if inst is not None else None
            if owner is not None and WProp.by_key(owner, NAME_PROP_KEY) is not None:
                wrapper = WObject.wrap(ref.uuid)
                label = cast(str | None, getattr(wrapper, NAME_PROP_KEY))
                if label:
                    return label
            return "" if inst is None else inst.name

        return MarkdownRenderer(ref_label).render(view)

    @classmethod
    @Database.commit_after_this
    def create_object(
        cls, type_name: str, props: dict[str, PropInput] | None = None
    ) -> ObjectView:
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is not None and owner.is_embedded:
            raise ValidationError(
                f"type {type_name!r} is embedded — its instances exist only as a prop value of an owner object"
            )
        normalized = cls._normalize_props(type_name, props or {})
        klass = WTypeMeta.python_class(type_name)
        if klass is not None:
            # **props forwarding: the dict can't collide with _uuid in
            # practice (prop keys), but the checker can't prove it
            ctor = cast(Callable[..., WObject], klass)
            instance_uuid = ctor(**normalized).uuid
        else:
            instance_uuid = WObject.create_db_only(type_name, normalized)
        # heal generated names: an embedded prop written before the name
        # prop in the same request computed a fallback-based child name
        WEmbedded.regenerate_names(instance_uuid)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    @Database.commit_after_this
    def update_object(cls, uuid: UUID, props: dict[str, PropInput]) -> ObjectView:
        from nylium.server.errors import ValidationError

        if instances[uuid].owner_object_uuid is not None:
            raise ValidationError(
                "embedded objects are edited through their owner — write the embedded prop on the parent instead"
            )
        wrapper = WObject.wrap(uuid)
        type_name = type_name_of(instances[uuid].type_uuid)
        normalized = cls._normalize_props(type_name, props)
        # ADR-0029: function-bound props are instance-level read-only.
        from nylium.tables.functions.instance_function_links import InstanceFunctionLinks

        bound_prop_uuids = {prop_uuid for prop_uuid, _ in InstanceFunctionLinks.function_links_of_instance(uuid)}
        if bound_prop_uuids:
            owner_type = WType.by_name(type_name)
            if owner_type is not None:
                bound_keys = {
                    p.key
                    for p in WProp.effective_for(owner_type)
                    if p.uuid in bound_prop_uuids
                }
                for key in normalized:
                    if key in bound_keys:
                        raise ValidationError(
                            f"prop {key!r} is computed by a function on this object — it is read-only"
                        )
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        # a renamed parent (or a reordered draft) invalidates the
        # generated names of its embedded children
        WEmbedded.regenerate_names(uuid)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    @classmethod
    @Database.commit_after_this
    def delete_object(cls, uuid: UUID) -> bool:
        from nylium.server.errors import ValidationError

        inst = instances.get(uuid)
        if inst is None:
            return False
        if inst.owner_object_uuid is not None:
            raise ValidationError(
                "embedded objects are deleted with their owner or by clearing the prop that holds them"
            )
        WObject.wrap(uuid).delete()
        return True
