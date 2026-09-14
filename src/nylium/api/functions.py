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
from nylium.api.display import FunctionView
from nylium.database import databasemethod
from nylium.tables import props, types
from nylium.tables.objects.types import Type
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import INPUT_PROP_KEY, WFunction
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WInteger, WNumeric
from nylium.objects.wtype import WType


class FunctionsApi(_FunctionsBase):
    @classmethod
    @databasemethod(commit=False)
    def list_functions(cls) -> list[FunctionView]:
        views = [FunctionView.from_uuid(uuid) for uuid in WFunction.instance_uuids()]
        return [view for view in views if view is not None]

    @classmethod
    @databasemethod(commit=False)
    def get_function(cls, uuid: UUID) -> FunctionView | None:
        return FunctionView.from_uuid(uuid)

    @classmethod
    @databasemethod(commit=True)
    def create_function(
        cls,
        input_type: str,
        output_type: str,
        name: str,
        input_object_uuid: UUID | None,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Create a Function<T,R> instance: validate the DAG draft before
        anything persists, materialize the parameterized type, create the
        object (name + input link), then save the graph, index deps and
        refuse a cross-function cycle. `nodes` items are (uuid, kind,
        position, config) — client-generated uuids so edges can reference
        them; `edges` items are (from_node_uuid, from_port, to_node_uuid,
        to_port)."""
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
        if input_object_uuid is not None:
            props_draft[INPUT_PROP_KEY] = input_object_uuid
        view = cls.create_object(owner.name, props_draft)
        WFunction.sync_graph(view.uuid, nodes, edges)
        WFunction.sync_deps(view.uuid)
        WFunction.assert_no_dependency_cycle()
        result = FunctionView.from_uuid(view.uuid)
        if result is None:
            raise RuntimeError(f"created function {view.uuid} vanished")
        return result

    @classmethod
    @databasemethod(commit=True)
    def update_function(
        cls,
        uuid: UUID,
        name: str,
        input_object_uuid: UUID | None,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Replace a function's DAG and re-point its input in one draft.
        The declared input/output types are fixed (they parameterize the
        type); only the graph, name and input link change here."""
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
        props_draft: dict[str, PropInput] = {NAME_PROP_KEY: name}
        if input_object_uuid is not None:
            props_draft[INPUT_PROP_KEY] = input_object_uuid
        _ = cls.update_object(uuid, props_draft)
        WFunction.sync_graph(uuid, nodes, edges)
        WFunction.sync_deps(uuid)
        WFunction.assert_no_dependency_cycle()
        result = FunctionView.from_uuid(uuid)
        if result is None:
            raise RuntimeError(f"updated function {uuid} vanished")
        return result

    @classmethod
    @databasemethod(commit=True)
    def delete_function(cls, uuid: UUID) -> bool:
        if FunctionView.from_uuid(uuid) is None:
            return False
        # unbind every prop computed through it first, then drop the object
        # (graph + deps cascade on the FK)
        for prop in props.where(function_uuid=uuid):
            prop.function_uuid = None
        return cls.delete_object(uuid)

    @classmethod
    @databasemethod(commit=True)
    def set_prop_function(
        cls, type_name: str, prop_key: str, function_uuid: UUID | None
    ) -> Type:
        """Bind a Function<T,R> instance to a prop (None unbinds). The
        function's output type must equal the prop's value type, and a
        formula-backed prop cannot become function-backed. Refuses a
        cross-function dependency cycle."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        prop = WProp.by_key(owner, prop_key)
        if prop is None:
            raise ValidationError(f"type {type_name!r} has no prop {prop_key!r}")
        if prop.is_trait_bound:
            raise ValidationError(
                f"prop {prop_key!r} is {WType.ANY_PREFIX}…>-bound and cannot run a function"
            )
        if function_uuid is not None:
            fn = FunctionView.from_uuid(function_uuid)
            if fn is None:
                raise ValidationError(f"{function_uuid} is not a function instance")
            if fn.output_type != prop.value_type().name:
                raise ValidationError(
                    f"function output {fn.output_type!r} does not match "
                    + f"prop type {prop.value_type().name!r}"
                )
        if prop.formula is not None:
            raise ValidationError(
                f"prop {prop_key!r} already has a formula — a prop cannot be both"
            )
        props[prop.uuid].function_uuid = function_uuid
        WFunction.assert_no_dependency_cycle()
        result = cls._type_result(type_name)
        return result

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
                Formula.validate(rewritten, dependent_schema, resolve_member_type)
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
        elif value_type_name != WNumeric.TYPE_NAME:
            raise ValidationError(
                f"a formula prop must be {WNumeric.TYPE_NAME} (or {WInteger.TYPE_NAME} for a bare COUNT), got {value_type_name!r}"
            )
        Formula.validate(formula, owner_type_props, cls._member_props)
