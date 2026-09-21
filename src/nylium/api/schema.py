"""Prop schema editing: reorder and full-draft prop sync (ADR-0015)."""
from __future__ import annotations

from uuid import UUID
from typing import TYPE_CHECKING

from nylium.api.shared import ApiShared, NAME_PROP_KEY

if TYPE_CHECKING:
    # see functions.py: cross-domain calls resolve on the combined Api
    from nylium.api.functions import FunctionsApi as _SchemaBase
else:
    _SchemaBase = ApiShared
from nylium.database import Database
from nylium.data.tables.objects.instances import instances
from nylium.data.tables.objects.props import props
from nylium.data.rows.objects.type import Type
from nylium.objects.wembedded import WEmbedded
from nylium.objects.wformula import Formula
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WString
from nylium.objects.wtype import WType
from nylium.server.errors import ValidationError


class SchemaApi(_SchemaBase):
    @classmethod
    @Database.commit_after_this
    def reorder_props(cls, type_name: str, keys: list[str]) -> Type:
        """Persist a new prop order; keys must cover the whole schema and
        keep the `name` prop first (see NAME_PROP_KEY)."""

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        existing = [prop.key for prop in WProp.all_for(owner)]
        if set(keys) != set(existing):
            raise ValueError(f"prop order {keys!r} does not match {type_name!r} schema")
        if (
            not owner.is_embedded
            and NAME_PROP_KEY in existing
            and (not keys or keys[0] != NAME_PROP_KEY)
        ):
            raise ValidationError(f"the {NAME_PROP_KEY!r} prop must stay first")
        WProp.reorder(owner, keys)
        return cls._type_result(type_name)

    @classmethod
    @Database.commit_after_this
    def sync_props(
        cls,
        type_name: str,
        items: list[tuple[UUID | None, str, str, str | None]],
        collects: dict[str, str] | None = None,
    ) -> Type:
        """Apply the type editor's full prop draft at once. Each item is
        (uuid | None, key, value type name, formula | None): a matching
        uuid edits that prop in place (rename/retype — a retype purges
        the old values), None creates a new prop, props absent from the
        draft are deleted for every instance at once. The pinned `name`
        prop must keep its uuid, its key, its String type and the first
        position. A formula (ADR-0005) must be Numeric, or Integer for a
        bare COUNT. collects maps prop key -> collect member key (ADR-0025)."""

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        existing = WProp.all_for(owner)
        by_uuid = {prop.uuid: prop for prop in existing}
        name_prop = next(
            (prop for prop in existing if prop.key == NAME_PROP_KEY), None
        )
        if not owner.is_embedded:
            # standalone types keep a pinned `name` prop first; embedded
            # composition types (ADR-0004) may omit it entirely (ADR-0027)
            if not items:
                raise ValidationError("a type must keep at least its 'name' prop")
            first_uuid, first_key, first_type, _ = items[0]
            if (
                name_prop is not None
                and (first_uuid, first_key, first_type)
                != (name_prop.uuid, NAME_PROP_KEY, WString.TYPE_NAME)
            ):
                raise ValidationError(
                    f"the {NAME_PROP_KEY!r} prop must stay first, keyed {NAME_PROP_KEY!r}, typed {WString.TYPE_NAME!r}"
                )
        keys = [key for _, key, _, _ in items]
        if any(not key.strip() for key in keys):
            raise ValidationError("prop keys must not be empty")
        for key in keys:
            cls._check_reserved_name(key, "prop key")
        if len(set(keys)) != len(keys):
            raise ValidationError(f"duplicate prop keys in {keys!r}")
        strangers = [uuid for uuid, _, _, _ in items if uuid is not None and uuid not in by_uuid]
        if strangers:
            raise ValidationError(f"prop uuids {strangers!r} do not belong to {type_name!r}")
        # ADR-0005 rename-rewrite, local pass: the editor echoes formulas
        # back verbatim, so a renamed key would otherwise fail validation
        # on the stale path. Rewrite array keys — and member keys of
        # self-referencing arrays — before checking against the new schema.
        renames = {
            by_uuid[uuid].key: key
            for uuid, key, _, _ in items
            if uuid is not None and by_uuid[uuid].key != key
        }
        self_arrays = {
            key
            for _, key, value_type_name, _ in items
            if WType.is_array_name(value_type_name)
            and WType.element_name(value_type_name) == type_name
        }
        if renames:
            items = [
                (
                    uuid,
                    key,
                    value_type_name,
                    Formula.rewrite(formula, renames, {k: renames for k in self_arrays})
                    if formula is not None
                    else None,
                )
                for uuid, key, value_type_name, formula in items
            ]
        owner_props = [(key, value_type_name) for _, key, value_type_name, _ in items]
        collects = dict(collects or {})
        collect_strangers = sorted(set(collects) - set(keys))
        if collect_strangers:
            raise ValidationError(
                f"collect keys {collect_strangers!r} do not name a prop of {type_name!r}"
            )
        for _, key, value_type_name, formula in items:
            collect = collects.get(key)
            if formula is not None and collect is not None:
                raise ValidationError(
                    f"prop {key!r} cannot be both a formula and a collect prop"
                )
            cls._check_formula_prop(formula, value_type_name, owner_props)
            cls._check_collect_prop(collect, value_type_name, owner_props)
        resolved = [
            (uuid, key, *cls._resolve_value_spec(value_type_name), formula, collects.get(key))
            for uuid, key, value_type_name, formula in items
        ]
        # cross-type pass: other types aggregate over Array<type_name>
        # props — rewrite their stored formulas to the new member keys, or
        # refuse the whole sync when a referenced member dies
        formula_updates = cls._rewrite_dependent_formulas(
            type_name, owner.uuid, owner_props, renames
        )
        # embedded children die with their prop: deleting or retyping an
        # embedded prop would cascade the link rows away and orphan the
        # child instances — destroy them while the prop still stands
        kept = {uuid: (key, vt) for uuid, key, vt, _, _, _ in resolved if uuid is not None}
        embedded_renamed = False
        for prop in existing:
            if prop.is_trait_bound:
                continue  # Any<…> has no concrete value type to compare
            old_value_type = prop.value_type()
            # composition-backed props — embedded links and Array<Embedded>
            # — own their child instances: deleting or retyping them would
            # cascade the link rows away and orphan the children, so destroy
            # them while the prop still stands (ADR-0021)
            if (
                not old_value_type.is_embedded
                and WEmbedded.array_element_type(old_value_type) is None
            ):
                continue
            draft = kept.get(prop.uuid)
            if draft is None or draft[1] != old_value_type.uuid:
                WEmbedded.destroy_children_of_prop(prop.uuid)
            elif draft[0] != prop.key:
                embedded_renamed = True
        WProp.sync_schema(owner, resolved)
        for prop_uuid, rewritten in formula_updates:
            props[prop_uuid].formula = rewritten
        if embedded_renamed:
            # a renamed embedded prop key invalidates every generated
            # child name of every instance of this type
            for instance_uuid in [i.uuid for i in instances.where(type_uuid=owner.uuid)]:
                WEmbedded.regenerate_names(instance_uuid)
        return cls._type_result(type_name)
