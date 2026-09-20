"""The raw `types` row mapping, in its own module so every table can
reference it without importing the domain layer (ADR-0011).

``props.py``/``unit_parts.py`` need to resolve type names and uuids in
SQL; if ``TABLE_Types`` lived in ``types.py`` those imports would cycle,
because ``types.py`` imports the child tables for the ``Type`` navigation
properties. Keeping the mapped class here — behaviour-free — makes
``table_types`` the shared bottom of the tables import DAG. The class is
re-exported from ``nylium.objects.tables.types`` so existing imports keep working.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_Types:
    """The raw `types` row — a plain mapped class, no behaviour (ADR-0011).

    Writers go through the ``Type`` domain object or the ``Types`` mapping
    in ``nylium.objects.tables.types`` (``create``/``update``/``delete``), never by
    constructing ``TABLE_Types`` directly. The mapped class stays
    importable where a SQL join needs the table — that is its only
    legitimate public use.
    """

    __tablename__: ClassVar[str] = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # ADR-0014: plural_name/icon/color live in type_decor (tables/decor),
    # 1:1 by uuid. This row carries identity + semantics only.
    # "object" (regular, builtin or array) | "enum" (string enum — its
    # values live in enum_options; instances never exist for enum types)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="object", server_default="object"
    )
    # Composition flag (ADR-0004): embedded types instantiate only as a
    # prop value of an owner object, never standalone. Orthogonal to
    # kind — an embedded type is still kind="object".
    embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
