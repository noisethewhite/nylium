"""Function<T,R> instances: DAG CRUD, prop binding, formula rewrites
(ADR-0007, ADR-0015)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from uuid import UUID

from nylium.api.shared import NAME_PROP_KEY, ApiShared, PropInput

if TYPE_CHECKING:
    # mixins resolve cross-domain calls on the combined Api facade; give the
    # checker the real base so create_object/update_object/delete_object are
    # known. At runtime all mixins inherit ApiShared and Api combines them.
    from nylium.api.objects import ObjectsApi as _FunctionsBase
else:
    _FunctionsBase = ApiShared
from nylium.api.display import FunctionView, ObjectView
from nylium.database import Database
from nylium.tables.objects import props, types
from nylium.tables.functions.instance_function_links import (
    delete_function_link,
    delete_links_to_function,
    instance_uuids_bound_to,
    merge_function_link,
)
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import WFunction
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WDate, WDatetime, WInteger, WNumeric, WString
from nylium.objects.wtype import WType


class FunctionsApi(_FunctionsBase):
    @classmethod
    @Database.use_same_session
    def list_functions(cls) -> list[FunctionView]:
        views = [FunctionView.from_uuid(uuid) for uuid in WFunction.instance_uuids()]
        return [view for view in views if view is not None]

    @classmethod
    @Database.use_same_session
    def get_function(cls, uuid: UUID) -> FunctionView | None:
        return FunctionView.from_uuid(uuid)

    @classmethod
    @Database.commit_after_this
    def create_function(
        cls,
        input_type: str,
        output_type: str,
        name: str,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Create a Function<T,R> instance (ADR-0029): validate the DAG
        draft before anything persists, materialize the parameterized type,
        create the object (name only — no input link), then save the graph.
        `nodes` items are (uuid, kind, position, config) — client-generated
        uuids so edges can reference them; `edges` items are
        (from_node_uuid, from_port, to_node_uuid, to_port)."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("function name must not be empty")
        cls._check_reserved_name(name, "function name")
        # validate the DAG before creating anything (fail-fast, no orphans)
        WFunction.validate_graph(
            [(uuid, kind, config) for uuid, kind, _, config in nodes],
            edges,
            input_type,
            output_type,
        )
        owner = WFunction.ensure_type(input_type, output_type)
        props_draft: dict[str, PropInput] = {NAME_PROP_KEY: name}
        view = cls.create_object(owner.name, props_draft)
        WFunction.sync_graph(view.uuid, nodes, edges)
        result = FunctionView.from_uuid(view.uuid)
        if result is None:
            raise RuntimeError(f"created function {view.uuid} vanished")
        return result

    @classmethod
    @Database.commit_after_this
    def update_function(
        cls,
        uuid: UUID,
        name: str,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Replace a function's DAG and rename it in one draft. The
        declared input/output types are fixed (they parameterize the type);
        only the graph and name change here. After the graph lands, re-run
        the per-owner cycle check on every object binding this function."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("function name must not be empty")
        existing = FunctionView.from_uuid(uuid)
        if existing is None:
            raise ValidationError(f"{uuid} is not a function instance")
        cls._check_reserved_name(name, "function name")
        WFunction.validate_graph(
            [(n_uuid, kind, config) for n_uuid, kind, _, config in nodes],
            edges,
            existing.input_type,
            existing.output_type,
        )
        _ = cls.update_object(uuid, {NAME_PROP_KEY: name})
        WFunction.sync_graph(uuid, nodes, edges)
        for owner_uuid in instance_uuids_bound_to(uuid):
            WFunction.assert_no_dependency_cycle(owner_uuid)
        result = FunctionView.from_uuid(uuid)
        if result is None:
            raise RuntimeError(f"updated function {uuid} vanished")
        return result

    @classmethod
    @Database.commit_after_this
    def delete_function(cls, uuid: UUID) -> bool:
        if FunctionView.from_uuid(uuid) is None:
            return False
        # unbind every (owner, prop) computed through it first, then drop
        # the object (graph + links cascade on the FK)
        delete_links_to_function(uuid)
        return cls.delete_object(uuid)

    @classmethod
    @Database.commit_after_this
    def set_instance_prop_function(
        cls, inst_uuid: UUID, prop_key: str, function_uuid: UUID | None
    ) -> ObjectView:
        """ADR-0029: bind a Function<T,R> to a specific prop of a specific
        object (None unbinds). The function's output type must equal the
        prop's value type; a formula- or collect-backed prop cannot become
        function-backed. Refuses a per-owner cross-function cycle."""
        from nylium.server.errors import ValidationError

        from nylium.tables.objects.instances import get as instance_get

        inst = instance_get(inst_uuid)
        if inst is None:
            raise ValidationError(f"no object {inst_uuid}")
        owner = WType.by_uuid(inst.type_uuid)
        if owner is None:
            raise ValidationError(f"object {inst_uuid} has no type")
        prop = WProp.by_key(owner, prop_key)
        if prop is None:
            raise ValidationError(
                f"type {owner.name!r} has no prop {prop_key!r}"
            )
        if prop.is_trait_bound:
            raise ValidationError(
                f"prop {prop_key!r} is {WType.ANY_PREFIX}…>-bound and cannot run a function"
            )
        if function_uuid is not None:
            fn = FunctionView.from_uuid(function_uuid)
            if fn is None:
                raise ValidationError(f"{function_uuid} is not a function instance")
            if fn.input_type != owner.name:
                raise ValidationError(
                    f"function reads {fn.input_type!r} siblings but the object is "
                    + f"a {owner.name!r}"
                )
            if fn.output_type != prop.value_type().name:
                raise ValidationError(
                    f"function output {fn.output_type!r} does not match "
                    + f"prop type {prop.value_type().name!r}"
                )
        if prop.formula is not None:
            raise ValidationError(
                f"prop {prop_key!r} already has a formula — a prop cannot be both"
            )
        if prop.collect is not None:
            raise ValidationError(
                f"prop {prop_key!r} is a collect prop — it cannot run a function"
            )
        if function_uuid is None:
            delete_function_link(inst_uuid, prop.uuid)
        else:
            merge_function_link(inst_uuid, prop.uuid, function_uuid)
        WFunction.assert_no_dependency_cycle(inst_uuid)
        view = ObjectView.from_uuid(inst_uuid)
        if view is None:
            raise RuntimeError(f"object {inst_uuid} vanished after function bind")
        return view

    # --- internals ---

    @classmethod
    def _member_props(cls, element_type_name: str) -> list[tuple[str, str]] | None:
        """The schema of an array's element type, for formula validation.
        None when the element type cannot be resolved at all."""
        element = WType.by_name(element_type_name)
        if element is None:
            return None
        # effective schema (ADR-0013); spec names keep Any<Trait> members
        # inspectable for formula validation
        return [
            (prop.key, prop.value_spec_name()) for prop in WProp.effective_for(element)
        ]

    @classmethod
    def _rewrite_dependent_formulas(
        cls,
        type_name: str,
        owner_uuid: UUID,
        new_schema: list[tuple[str, str]],
        renames: dict[str, str],
    ) -> list[tuple[UUID, str]]:
        """ADR-0005 rename-rewrite, cross-type pass: formulas on OTHER
        types that aggregate over ``Array<type_name>`` props are rewritten
        to the renamed member keys and re-validated against the new
        schema. A formula that still reads a deleted or retyped member
        fails the whole sync — schemas never strand a stored formula.
        Returns (prop uuid, new formula) updates; the caller persists
        them after the local schema change lands."""
        array_type_row = next(types.where(name=WType.array_name(type_name)), None)
        if array_type_row is None:
            return []

        def resolve_member_type(element_name: str) -> list[tuple[str, str]] | None:
            if element_name == type_name:
                return new_schema
            return cls._member_props(element_name)

        updates: list[tuple[UUID, str]] = []
        usages = [
            (p.owner_type_uuid, p.key)
            for p in props.where(value_type_uuid=array_type_row.uuid)
        ]
        by_owner: dict[UUID, list[str]] = {}
        for dependent_uuid, array_key in usages:
            # None: trait-owned array props carry no formulas to rewrite (v1)
            if dependent_uuid is None or dependent_uuid == owner_uuid:
                continue  # self-referencing arrays were rewritten locally
            by_owner.setdefault(dependent_uuid, []).append(array_key)
        for dependent_uuid, array_keys in by_owner.items():
            dependent = WType.by_uuid(dependent_uuid)
            if dependent is None:
                continue
            dependent_props = WProp.all_for(dependent)
            # spec names: a trait-bound prop has no concrete value type
            dependent_schema = [
                (prop.key, prop.value_spec_name()) for prop in dependent_props
            ]
            member_renames = {key: renames for key in array_keys}
            for prop in dependent_props:
                if prop.formula is None:
                    continue
                rewritten = Formula.rewrite(prop.formula, {}, member_renames)
                Formula.validate(rewritten, dependent_schema, resolve_member_type, cls._is_string_like)
                if rewritten != prop.formula:
                    updates.append((prop.uuid, rewritten))
        return updates

    @classmethod
    def _check_formula_prop(
        cls,
        formula: str | None,
        value_type_name: str,
        owner_type_props: list[tuple[str, str]],
    ) -> None:
        """Validate a prop's formula (ADR-0005) against the owner schema.
        A formula prop must be Numeric — or Integer for a bare COUNT."""
        from nylium.server.errors import ValidationError

        if formula is None:
            return
        if value_type_name == WInteger.TYPE_NAME:
            if not Formula.is_bare_count(formula):
                raise ValidationError(
                    "an Integer formula prop must be a bare COUNT(<array>) call"
                )
        elif value_type_name != WNumeric.TYPE_NAME and WType.unit_param_of(value_type_name) is None:
            raise ValidationError(
                f"a formula prop must be {WNumeric.TYPE_NAME} (or {WInteger.TYPE_NAME} for a bare COUNT, or Numeric<Unit>), got {value_type_name!r}"
            )
        Formula.validate(formula, owner_type_props, cls._member_props, cls._is_string_like)

    @classmethod
    def _is_ordered_scalar(cls, spec_name: str) -> bool:
        """ADR-0025: a value spec that supports a [from, to] range comparison."""
        return (
            spec_name
            in {
                WInteger.TYPE_NAME,
                WNumeric.TYPE_NAME,
                WDate.TYPE_NAME,
                WDatetime.TYPE_NAME,
            }
            or WType.unit_param_of(spec_name) is not None
        )

    @classmethod
    def _is_string_like(cls, spec_name: str) -> bool:
        """ADR-0024: a String or enum spec — the families an IF condition may
        compare against a quoted literal."""
        if spec_name == WString.TYPE_NAME:
            return True
        target = WType.by_name(spec_name)
        return target is not None and target.is_enum

    @classmethod
    def _check_collect_prop(
        cls,
        collect: str | None,
        value_type_name: str,
        owner_type_props: list[tuple[str, str]],
    ) -> None:
        """ADR-0025: a collect prop is an Array<T> whose element type T has an
        ordered scalar member named by `collect`; the owner must define
        `from`/`to` props of exactly that value spec."""
        from nylium.server.errors import ValidationError

        if collect is None:
            return
        if not WType.is_array_name(value_type_name):
            raise ValidationError(
                f"a collect prop must be an array (Array<T>), got {value_type_name!r}"
            )
        element_name = WType.element_name(value_type_name)
        element = WType.by_name(element_name)
        if element is None:
            raise ValidationError(f"collect target type {element_name!r} does not exist")
        if element.is_embedded:
            raise ValidationError(
                f"collect target {element_name!r} is embedded — collect works over standalone types"
            )
        member_spec = next(
            (
                spec
                for key, spec in (cls._member_props(element_name) or [])
                if key == collect
            ),
            None,
        )
        if member_spec is None:
            raise ValidationError(f"collect member {collect!r} not found on {element_name!r}")
        if not cls._is_ordered_scalar(member_spec):
            raise ValidationError(
                f"collect member {collect!r} of {element_name!r} is not an ordered scalar "
                + "(Numeric, Integer, Date, Datetime, or Numeric<Unit>)"
            )
        owner_spec = dict(owner_type_props)
        for bound in ("from", "to"):
            if owner_spec.get(bound) != member_spec:
                raise ValidationError(
                    f"a collect prop requires the owner to define {bound!r} as {member_spec!r}"
                )
