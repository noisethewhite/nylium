"""Trait CRUD and attach/detach to user types (ADR-0015)."""
from __future__ import annotations

from uuid import UUID

from nylium.api.ApiShared import ApiShared
from nylium.database import Database
from nylium.data.rows import Trait
from nylium.data.tables import instances
from nylium.data.tables import props
from nylium.data.tables import traits
from nylium.data.tables import type_traits
from nylium.data.tables import trait_decor
from nylium.data.rows import SchemaItem
from nylium.data.rows import Type
from nylium.data.tables import types
from nylium.objects.navigation import trait_color, trait_props
from nylium.objects.nyprop import NyProp
from nylium.objects.nyscalar import NyScalar
from nylium.objects.NyType import NyType
from nylium.server.errors import ValidationError


class TraitsApi(ApiShared):
    @classmethod
    @Database.use_same_session
    def list_traits(cls) -> list[Trait]:
        return list(traits.all())

    @classmethod
    @Database.use_same_session
    def get_trait(cls, name: str) -> Trait | None:
        return next(traits.where(name=name), None)

    @classmethod
    @Database.commit_after_this
    def create_trait(
        cls, name: str, color: str, props: dict[str, str] | None = None
    ) -> Trait:
        """props maps key -> value spec (a concrete type name or
        Any<TraitName>). Dict order becomes the display order. Traits v1
        have no name prop and no formulas — they're prop bundles, not
        types."""

        final_name = name.strip()
        if not final_name:
            raise ValidationError("trait name must not be empty")
        cls._check_reserved_name(final_name, "trait name")
        if NyType.is_any_name(final_name):
            raise ValidationError(
                f"trait name {final_name!r} collides with the {NyType.ANY_PREFIX}…> grammar"
            )
        if next(traits.where(name=final_name), None) is not None:
            raise ValueError(f"trait {final_name!r} already exists")
        cls._check_color(color)
        specs = dict(props or {})
        for key in specs:
            if not key.strip():
                raise ValidationError("prop keys must not be empty")
            cls._check_reserved_name(key, "prop key")
        NyScalar.ensure_builtins()
        resolved: list[SchemaItem] = [
            (None, key, *cls._resolve_value_spec(spec), None, None)
            for key, spec in specs.items()
        ]
        trait = traits.create(final_name, color)
        NyProp.sync_trait_schema(trait.uuid, resolved)
        return cls._trait_result(final_name)

    @classmethod
    @Database.commit_after_this
    def sync_trait(
        cls,
        name: str,
        new_name: str | None = None,
        color: str | None = None,
        items: list[tuple[UUID | None, str, str, str | None]] | None = None,
    ) -> Trait:
        """Edit a trait's identity and/or prop draft. items is the same
        (uuid | None, key, value spec, formula | None) shape as sync_props
        — traits v1 have no formulas, so the fourth element must be None.
        A retype/deleted prop purges values of every attached type's
        instances (inside sync_trait_schema)."""

        row = next(traits.where(name=name), None)
        if row is None:
            raise KeyError(f"no trait {name!r}")
        final_name = name if new_name is None else new_name.strip()
        if not final_name:
            raise ValidationError("trait name must not be empty")
        cls._check_reserved_name(final_name, "trait name")
        if NyType.is_any_name(final_name):
            raise ValidationError(
                f"trait name {final_name!r} collides with the {NyType.ANY_PREFIX}…> grammar"
            )
        collision = next(traits.where(name=final_name), None)
        if collision is not None and collision.uuid != row.uuid:
            raise ValueError(f"trait {final_name!r} already exists")
        final_color = trait_color(row.uuid) if color is None else color
        if color is not None:
            cls._check_color(color)
        if items is not None:
            if not items:
                raise ValidationError(f"trait {name!r} must keep at least one prop")
            existing = {p.uuid for p in props.where(owner_trait_uuid=row.uuid)}
            keys = [key for _, key, _, _ in items]
            if any(not key.strip() for key in keys):
                raise ValidationError("prop keys must not be empty")
            for key in keys:
                cls._check_reserved_name(key, "prop key")
            if len(set(keys)) != len(keys):
                raise ValidationError(f"duplicate prop keys in {keys!r}")
            if any(formula is not None for _, _, _, formula in items):
                raise ValidationError("traits v1 have no formula props")
            strangers = [
                uuid for uuid, _, _, _ in items
                if uuid is not None and uuid not in existing
            ]
            if strangers:
                raise ValidationError(
                    f"prop uuids {strangers!r} do not belong to trait {name!r}"
                )
            resolved: list[SchemaItem] = [
                (uuid, key, *cls._resolve_value_spec(spec), None, None)
                for uuid, key, spec, _ in items
            ]
            NyProp.sync_trait_schema(row.uuid, resolved)
        row.name = final_name
        trait_decor[row.uuid].color = final_color
        return cls._trait_result(final_name)

    @classmethod
    @Database.commit_after_this
    def delete_trait(cls, name: str) -> bool:
        """Refuses while the trait is attached to any type or used as an
        Any<> bound — the error names the dependents."""
        row = next(traits.where(name=name), None)
        if row is None:
            return False
        attached: list[str] = []
        for link in type_traits.where(trait_uuid=row.uuid):
            owner = types.get(link.type_uuid)
            attached.append("<gone>" if owner is None else owner.name)
        bound_owners: list[str] = []
        for p in props.where(value_trait_uuid=row.uuid):
            if p.owner_trait_uuid is not None:
                owner_trait = traits.get(p.owner_trait_uuid)
                bound_owners.append(
                    "<gone>" if owner_trait is None else f"trait {owner_trait.name}"
                )
            elif p.owner_type_uuid is not None:
                owner_type = types.get(p.owner_type_uuid)
                bound_owners.append(
                    "<gone>" if owner_type is None else f"type {owner_type.name}"
                )
        if attached or bound_owners:
            parts: list[str] = []
            if attached:
                parts.append(f"attached to {sorted(attached)!r}")
            if bound_owners:
                parts.append(
                    f"used as {NyType.ANY_PREFIX}{name}> bound on {sorted(bound_owners)!r}"
                )
            raise ValueError(f"trait {name!r} is still " + " and ".join(parts))
        traits.delete(row.uuid)  # its props cascade
        return True

    @classmethod
    @Database.commit_after_this
    def attach_trait(cls, type_name: str, trait_name: str) -> Type:
        """Attach a trait to a user type. Prop keys must not collide with
        the type's current effective schema."""

        owner = NyType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        trait = next(traits.where(name=trait_name), None)
        if trait is None:
            raise KeyError(f"no trait {trait_name!r}")
        links = list(type_traits.where(type_uuid=owner.uuid))
        if any(link.trait_uuid == trait.uuid for link in links):
            raise ValueError(f"trait {trait_name!r} is already attached to {type_name!r}")
        taken = {p.key for p in NyProp.effective_for(owner)}
        collisions = sorted({p.key for p in trait_props(trait.uuid)} & taken)
        if collisions:
            raise ValidationError(
                f"prop keys {collisions!r} of trait {trait_name!r} collide with {type_name!r}"
            )
        position = max((link.position for link in links), default=-1) + 1
        _ = type_traits.attach(owner.uuid, trait.uuid, position)
        return cls._type_result(type_name)

    @classmethod
    @Database.commit_after_this
    def detach_trait(cls, type_name: str, trait_name: str) -> Type:
        """Detach a trait; the trait prop values of this type's instances
        are purged (the trait itself and its other types keep theirs)."""
        owner = NyType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        trait = next(traits.where(name=trait_name), None)
        if trait is None:
            raise KeyError(f"no trait {trait_name!r}")
        link = next(
            (
                edge
                for edge in type_traits.where(type_uuid=owner.uuid)
                if edge.trait_uuid == trait.uuid
            ),
            None,
        )
        if link is None:
            raise KeyError(f"trait {trait_name!r} is not attached to {type_name!r}")
        inst_uuids = [i.uuid for i in instances.where(type_uuid=owner.uuid)]
        for p in props.where(owner_trait_uuid=trait.uuid):
            NyProp.purge_values_for_instances(p.uuid, inst_uuids)
        type_traits.detach(owner.uuid, trait.uuid)
        return cls._type_result(type_name)
