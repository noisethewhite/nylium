"""Request bodies for the HTTP boundary.

The props payload reuses the same discriminated shape the API renders
(ScalarValue / RefValue / ArrayValue): one wire contract in both
directions, no parallel input hierarchy.

File-level exception to one-class-per-file: these are peer request
DTOs of the same boundary, mirroring the views they pair with.
"""
from __future__ import annotations

from dataclasses import field
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.api.views import PropValue
from nylium.objects.wscalar import WColor

_CONFIG = ConfigDict(extra="ignore")


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


@dataclass(config=_CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)


@dataclass(config=_CONFIG)
class ReorderPropsBody:
    """New ordering for a type's props, as a full list of prop keys."""

    keys: list[str]


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


@dataclass(config=_CONFIG)
class CreateEnumBody:
    """A string enum type: name plus its allowed option values."""

    name: str
    options: list[str] = field(default_factory=list)
    icon: str = "lists"
    color: str = WColor.DEFAULT


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


@dataclass(config=_CONFIG)
class UpdateTypeBody:
    """PATCH semantics: only the listed fields change."""

    name: str | None = None
    plural_name: str | None = None
    icon: str | None = None
    color: str | None = None


@dataclass(config=_CONFIG)
class RenameFileBody:
    """ADR-0008: rename a file entity's display name. The uuid pointer is
    stable, so references never break."""

    name: str


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


@dataclass(config=_CONFIG)
class UpdateFunctionBody:
    """Replace a function's name, input link and DAG (full-draft PUT
    semantics — the input/output parameterization is fixed)."""

    name: str
    input_object_uuid: UUID | None = None
    nodes: list[FunctionNodeInput] = field(default_factory=list)
    edges: list[FunctionEdgeInput] = field(default_factory=list)


@dataclass(config=_CONFIG)
class SetPropFunctionBody:
    """Bind a Function<T,R> instance to a prop (None unbinds)."""

    function_uuid: UUID | None = None


@dataclass(config=_CONFIG)
class CreateTraitBody:
    """A trait (ADR-0013): name, color, and a prop bundle — the same
    key -> value spec shape as CreateTypeBody.props."""

    name: str
    props: dict[str, str] = field(default_factory=dict)
    color: str = WColor.DEFAULT


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


@dataclass(config=_CONFIG)
class TraitAttachBody:
    """Attach/detach a trait to/from a type."""

    trait: str

