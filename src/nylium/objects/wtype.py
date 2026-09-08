"""WType: handle on a row of the `types` table.

Owns the type-name conventions, including the generic array type name
(`Array<Element>`) shared by class materialization and attribute IO.

Prop queries live on WProp, not here: wprop imports wtype (for
value_type), so wtype must not import wprop back — that keeps the
objects package a DAG.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import databasemethod
from nylium.tables.objects.types import Type, types


class WType:
    ARRAY_TYPE_PREFIX: ClassVar[str] = "Array<"
    UNIT_NUMERIC_PREFIX: ClassVar[str] = "Numeric<"
    FUNCTION_PREFIX: ClassVar[str] = "Function<"
    KIND_OBJECT: ClassVar[str] = "object"
    KIND_ENUM: ClassVar[str] = "enum"
    KIND_UNIT: ClassVar[str] = "unit"
    KIND_FUNCTION: ClassVar[str] = "function"
    KIND_FILE: ClassVar[str] = "file"

    def __init__(self, row: Type):
        # snapshot, not a live row: reads must not depend on the session
        # that fetched the row still being open
        self._uuid: UUID = row.uuid
        self._name: str = row.name
        self._plural_name: str = row.plural_name
        self._icon: str = row.icon
        self._color: str = row.color
        self._kind: str = row.kind
        self._embedded: bool = row.embedded

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def name(self) -> str:
        return self._name

    @property
    def plural_name(self) -> str:
        return self._plural_name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def color(self) -> str:
        return self._color

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def is_enum(self) -> bool:
        return self._kind == self.KIND_ENUM

    @property
    def is_unit(self) -> bool:
        return self._kind == self.KIND_UNIT

    @property
    def is_function(self) -> bool:
        return self._kind == self.KIND_FUNCTION

    @property
    def is_file(self) -> bool:
        return self._kind == self.KIND_FILE

    @property
    def is_embedded(self) -> bool:
        return self._embedded

    # --- type-name conventions ---

    @classmethod
    def array_name(cls, element_name: str) -> str:
        return f"{cls.ARRAY_TYPE_PREFIX}{element_name}>"

    @classmethod
    def is_array_name(cls, name: str) -> bool:
        return name.startswith(cls.ARRAY_TYPE_PREFIX) and name.endswith(">")

    @classmethod
    def element_name(cls, array_name: str) -> str:
        return array_name[len(cls.ARRAY_TYPE_PREFIX) : -1]

    @classmethod
    def unit_numeric_name(cls, unit_name: str) -> str:
        """The prop value type parameterized on a unit: Numeric<Temperature>."""
        return f"{cls.UNIT_NUMERIC_PREFIX}{unit_name}>"

    @classmethod
    def unit_param_of(cls, type_name: str) -> str | None:
        """Syntactic split only — 'Numeric<Temperature>' -> 'Temperature'.
        Whether the parameter actually names a unit type is WUnit's
        semantic check; arrays never match (they start with Array<)."""
        if type_name.startswith(cls.UNIT_NUMERIC_PREFIX) and type_name.endswith(">"):
            return type_name[len(cls.UNIT_NUMERIC_PREFIX) : -1]
        return None

    @classmethod
    def function_name(cls, input_name: str, output_name: str) -> str:
        """The parameterized function type name: Function<T, R>."""
        return f"{cls.FUNCTION_PREFIX}{input_name}, {output_name}>"

    @classmethod
    def is_function_name(cls, name: str) -> bool:
        return name.startswith(cls.FUNCTION_PREFIX) and name.endswith(">")

    @classmethod
    def function_params(cls, type_name: str) -> tuple[str, str] | None:
        """Syntactic split only — 'Function<Invoice, Numeric>' ->
        ('Invoice', 'Numeric'). The comma is the single separator because
        neither T (an object kind) nor R (a scalar) can itself contain a
        comma."""
        if not cls.is_function_name(type_name):
            return None
        inner = type_name[len(cls.FUNCTION_PREFIX) : -1]
        input_name, sep, output_name = inner.partition(",")
        if not sep:
            return None
        return (input_name.strip(), output_name.strip())

    # --- row access ---

    @classmethod
    @databasemethod(commit=False)
    def by_name(cls, name: str) -> "WType | None":
        row = next(types.where(name=name), None)
        return None if row is None else cls(row)

    @classmethod
    @databasemethod(commit=False)
    def by_uuid(cls, uuid: UUID) -> "WType | None":
        row = types.get(uuid)
        return None if row is None else cls(row)

    @classmethod
    @databasemethod(commit=True)
    def ensure(
        cls,
        name: str,
        plural_name: str | None = None,
        icon: str | None = None,
        kind: str | None = None,
        embedded: bool | None = None,
    ) -> "WType":
        existing = cls.by_name(name)
        if existing is not None:
            if kind is not None and existing.kind != kind:
                raise ValueError(
                    f"type {name!r} already exists as {existing.kind}, not {kind}"
                )
            # embedded is a create-time declaration: callers that pass it
            # must agree with the existing row, silent flag flips would
            # strand or orphan instances
            if embedded is not None and existing.is_embedded != embedded:
                raise ValueError(
                    f"type {name!r} already exists as {'embedded' if existing.is_embedded else 'standalone'}"
                )
            # builtins re-ensure on every boot: keep their icon canonical
            if icon is not None and existing.icon != icon:
                row = types[existing.uuid]
                row.icon = icon
                return cls(row)
            return existing
        row = types.create(name, plural_name or f"{name}s", icon=icon, kind=kind, embedded=embedded)
        return cls(row)
