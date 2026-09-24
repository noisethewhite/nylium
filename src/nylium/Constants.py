"""Reusable cross-layer constants, one class with category subclasses.

Every constant shared between layers lives here, grouped by domain
(``Constants.Scalar.STRING``, ``Constants.Pydantic.VIEW_CONFIG``) instead
of a per-domain module zoo or, worse, the same literal re-declared in four
places (``NAME_PROP_KEY`` was defined in five modules).

The module MUST stay an import leaf: stdlib + pydantic only, never another
nylium module — the tables layer AND the objects layer both import this,
so any nylium import here closes a cycle (same constraint the old
``scalar_type_names`` leaf served, ADR-0031).

Category classes are namespaces, not instantiable types.
"""
from __future__ import annotations

from typing import ClassVar, final

from pydantic import ConfigDict


@final
class Constants:
    """The reusable-constant vocabulary, grouped by category."""

    class Scalar:
        """Canonical value-type names — the ``TYPE_NAME`` of each scalar wrapper."""

        STRING: ClassVar[str] = "String"
        INTEGER: ClassVar[str] = "Integer"
        NUMERIC: ClassVar[str] = "Numeric"
        BOOLEAN: ClassVar[str] = "Boolean"
        DATETIME: ClassVar[str] = "Datetime"
        DATE: ClassVar[str] = "Date"
        TIME: ClassVar[str] = "Time"
        COLOR: ClassVar[str] = "Color"
        MONTH_DAY: ClassVar[str] = "MonthDay"
        MONTH_DAY_TIME: ClassVar[str] = "MonthDayTime"

        # Sibling names are visible here because this is the SAME class
        # body — a nested category could not reference them.
        NUMERIC_SCALARS: ClassVar[frozenset[str]] = frozenset({INTEGER, NUMERIC})

    class Props:
        """Prop keys pinned by the domain, identical on every object type."""

        # The object title prop, pinned first on every object type; tags and
        # markdown derive the owner's display name from it.
        NAME_PROP_KEY: ClassVar[str] = "name"
        # The one prop every scalar type carries.
        VALUE_PROP_KEY: ClassVar[str] = "value"

    class Types:
        """Type-vocabulary markers shared by the meta/type layers."""

        NYOBJECT_ROOT_NAME: ClassVar[str] = "NyObject"
        PRIVATE_PREFIX: ClassVar[str] = "_"
        LIST_ANNOTATION_PREFIX: ClassVar[str] = "list["
        ARRAY_INSTANCE_NAME: ClassVar[str] = "array"

    class Objects:
        """Instance naming vocabulary."""

        SHORT_UUID_LENGTH: ClassVar[int] = 8
        INSTANCE_NAME_FORMAT: ClassVar[str] = "{type_name}:{short_uuid}"

    class Embedded:
        """Embedded-composition markers (ADR-0004)."""

        # Reserved glyph in generated child names; banned from user naming.
        NAME_SEPARATOR: ClassVar[str] = "→"

    class Functions:
        """NyFunction vocabulary (ADR-0007/0018): the closed node-kind set."""

        NODE_GET_PROP: ClassVar[str] = "get_prop"
        NODE_CONST: ClassVar[str] = "const"
        NODE_ADD: ClassVar[str] = "add"
        NODE_SUB: ClassVar[str] = "sub"
        NODE_MUL: ClassVar[str] = "mul"
        NODE_DIV: ClassVar[str] = "div"
        NODE_SUM: ClassVar[str] = "sum"
        NODE_AVERAGE: ClassVar[str] = "average"
        NODE_COUNT: ClassVar[str] = "count"
        NODE_MIN: ClassVar[str] = "min"
        NODE_MAX: ClassVar[str] = "max"
        NODE_CAST: ClassVar[str] = "cast"
        NODE_MAP: ClassVar[str] = "map"

    class Formulas:
        """Formula-DSL vocabulary (ADR-0023)."""

        FUNCTIONS: ClassVar[frozenset[str]] = frozenset({"SUM", "AVERAGE", "COUNT", "MIN", "MAX"})

    class Pydantic:
        """Shared pydantic configs for wire DTOs and request bodies."""

        # Tolerant: ignore extra fields (request bodies, read-side DTOs).
        CONFIG: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
        # Strict wire DTO config (the old per-file ``_VIEW_CONFIG``).
        VIEW_CONFIG: ClassVar[ConfigDict] = ConfigDict(strict=True)

    class Server:
        """``nylium serve`` defaults."""

        APP_FACTORY: ClassVar[str] = "nylium.server.NyliumApp:NyliumApp.create"
        DEFAULT_HOST: ClassVar[str] = "127.0.0.1"
        DEFAULT_PORT: ClassVar[int] = 8000

    class Auth:
        """HTTP auth vocabulary."""

        BEARER_PREFIX: ClassVar[str] = "Bearer "

    class Render:
        """Markdown-render placeholders (``api/MarkdownRenderer``)."""

        UNSET: ClassVar[str] = "—"
        EMPTY_ARRAY: ClassVar[str] = "∅"
