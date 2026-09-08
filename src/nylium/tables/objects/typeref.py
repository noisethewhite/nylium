"""The raw `types` row mapping, in its own module so every table can
reference it without importing the domain layer (ADR-0011).

``props.py``/``unit_parts.py`` need to resolve type names and uuids in
SQL; if ``TABLE_Types`` lived in ``types.py`` those imports would cycle,
because ``types.py`` imports the child tables for the ``Type`` navigation
properties. Keeping the mapped class here — behaviour-free — makes
``typeref`` the shared bottom of the tables import DAG. The class is
re-exported from ``nylium.tables.objects.types`` so existing imports keep working.
"""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.tables.base import Base


class TABLE_Types(Base):
    """The raw `types` row — a plain mapped class, no behaviour (ADR-0011).

    Writers go through the ``Type`` domain object or the ``Types`` mapping
    in ``nylium.tables.objects.types`` (``create``/``update``/``delete``), never by
    constructing ``TABLE_Types`` directly. The mapped class stays
    importable where a SQL join needs the table — that is its only
    legitimate public use.
    """

    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Every type carries both forms, builtins included (ADR-0011 phase 8);
    # WType.ensure derives "<name>s" when the caller passes no plural
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Material Symbols name, rendered monochrome by the UI;
    # server defaults backfill existing rows on ALTER
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    # ADR-0005: stores #RRGGBB hex; the default must match WColor.DEFAULT
    # (tables must not import objects — keep the literal in sync by hand)
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )
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
